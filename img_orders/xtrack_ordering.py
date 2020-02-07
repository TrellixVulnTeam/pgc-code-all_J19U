# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 13:08:08 2020

@author: disbr007
"""

import argparse
import os

import pandas as pd
from tqdm import tqdm

from selection_utils.query_danco import query_footprint, count_table
from misc_utils.logging_utils import create_logger
from misc_utils.utm_area_calc import area_calc
from misc_utils.id_parse_utils import write_ids, get_platform_code, mfp_ids


# INPUTS
out_path = r''
num_ids = 40_000 # Desired number of IDs
sensors = ['WV01', 'WV02', 'WV03']

min_date = '2019-04-23'
max_date = None

max_area = None # Max overlap area to include
min_area = 1000 # Min overlap area to include


def xtrack_ordering(out_path, num_ids, min_date, max_date,
                    min_area, max_area, sensors):
    """
    Select IDs from the danco xtrack footprint, given the 
    arguments above, sorted by maximum area first.

    Parameters
    ----------
    out_path : os.path.abspath
        Path to write ID selection .txt to.
    num_ids : INT
        Number of IDs desired.
    min_date : STR
        Minimum year to consider.
    max_date : STR
        Maximum year to consider.
    min_area : FLOAT
        Minimum area to consider.
    max_area : FLOAT
        Maximum area to consider.
    sensors : LIST
        Sensors to consider: e.g. ["WV01", "WV02"]

    Returns
    ---------
    set : selected catalog ids
    
    """
    
    def check_where(where):
        if where:
            where += ' AND '
        return where
    
    # Parameters
    area_col = 'sqkm_utm'
    
    logger = create_logger(os.path.basename(__file__), 'sh',
                           handler_level='INFO')
    
    # Load footprints in chunks to avoid long load time
    # Xtrack table name
    xtrack_name = 'dg_imagery_index_xtrack_cc20'
    # Columns to load
    cols = ['objectid', 'catalogid1', 'catalogid2', 'acqdate1', 'pairname']
    
    # Build where clause
    where = ""
    if min_date:
        where = check_where(where)
        where += "(acqdate1 > '{}')".format(min_date)
    if max_date:
        where = check_where(where)
        where += "(acqdate1 < '{}')".format(max_date)
    # Add platforms to where, there are no platform fields in the xtrack table
    # so using first three digits of catalogid
    if sensors:
        sensor_where = ''
        for sensor in sensors:
            if sensor_where:
                sensor_where += ' OR '
            sensor_where += """(catalogid1 LIKE '{0}%%' OR catalogid2 LIKE '{0}%%')""".format(get_platform_code(sensor))
        if where:
            where += " AND "
        where += '({})'.format(sensor_where)
    
    # Count the number of records returned by the where sql query
    
    xt_size = count_table(xtrack_name, columns=[cols[0]], where=where)
    logger.info('Size of full selection would be: {:,}'.format(xt_size))
        
    chunksize = 500_000
    logger.info('Loading in chunks of {:,}'.format(chunksize))
    
    prev_x = 0
    xt_chunks = [] # list to store dataframe chunks
    tbl_size = count_table(xtrack_name, columns=[cols[0]])
    for x in range(0, tbl_size+chunksize, chunksize):
        if x == 0:
            continue
        logger.info('Loading {} chunk: {:,} - {:,}'.format(xtrack_name, prev_x, x))
        # Add objectid range to sql clause
        obj_where = """{} AND (objectid >= {} AND objectid < {})""".format(where, prev_x, x)

        logger.debug('Where clause to apply to {}:\n{}'.format(xtrack_name, obj_where))
        xt_chunk = query_footprint(xtrack_name, 
                                    where=obj_where,
                                    columns=cols)
        loaded_records = len(xt_chunk)
        logger.info('Number of records loaded from chunk: {:,}'.format(loaded_records))
        logger.debug('min objectid: {}'.format(xt_chunk.objectid.min()))
        logger.debug('max objectid: {}'.format(xt_chunk.objectid.max()))
        
        if loaded_records != 0:
            # Calculate UTM area
            # TODO: Rewrite this to be an apply function
            logger.info('Calculating utm area on chunk...')
            xt_chunk = area_calc(xt_chunk, area_col=area_col)
            if min_area and max_area:
                xt_chunk = xt_chunk[(xt_chunk[area_col] > min_area) & (xt_chunk[area_col] <= max_area)]
            elif min_area:
                xt_chunk = xt_chunk[xt_chunk[area_col] > min_area]
            elif max_area:
                xt_chunk = xt_chunk[xt_chunk[area_col] <= max_area]
                
            logger.info('Number of records meeting area specification (if any): {:,}'.format(len(xt_chunk)))
            xt_chunks.append(xt_chunk)
        
        prev_x = x
        
        
    xt_area = pd.concat(xt_chunks)
    
    # Sort by area, max first, then get first n records
    xt_area.sort_values(by=area_col, ascending=False, inplace=True)
    
    logger.info('Summary of all matching footprints:\n{}'.format(xt_area.describe()))
    
    # Iterate over footprints, max first, adding to list if not already in and not in mfp
    # until number ids is reached or footprints are exhausted.
    logger.info('Collecting catalogids, starting with largest area...')
    unique_ids = set()
    oh_ids = set(mfp_ids())
    pbar = tqdm(xt_area.iterrows(), total=len(xt_area))
    # for i, row in tqdm(xt_area.iterrows()):
    for i, row in pbar:
        id1 = row['catalogid1']
        id2 = row['catalogid2']
        if id1 not in oh_ids:
            unique_ids.add(id1)
        if id2 not in oh_ids:
            unique_ids.add(id2)

        unique_count = len(set(unique_ids))
        pbar.set_description_str('Unique IDs found: {:,}'.format(unique_count))
        if unique_count >= num_ids:
            break
    
    
    selected_ids = set(unique_ids)
    
    logger.info('Writing {:,} selected IDs to {}...'.format(len(selected_ids), out_path))
    write_ids(selected_ids, out_path)
    
    
# xtrack_ordering(out_path, num_ids, min_date, max_date, min_area, max_area, sensors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('out_path', type=os.path.abspath,
                        help='Path to write list of selected IDs.')
    parser.add_argument('--num_ids', type=int,
                        help='Number of IDs to select.')
    parser.add_argument('--min_date', type=str,
                        help='Minimum acqdate to consider. E.g.: 2019-04-21')
    parser.add_argument('--max_date', type=str,
                        help='Maximum acqdate to consider.')
    parser.add_argument('--min_area', type=float,
                        help='Minimum footprint area to consider.')
    parser.add_argument('--max_area', type=float,
                        help='Maximum footprint area to consider.')
    parser.add_argument('--sensors', nargs='+', default=['WV01', 'WV02', 'WV03'],
                        help='Sensors to consider.')
    
    args = parser.parse_args()
    
    out_path = args.out_path
    num_ids = args.num_ids
    min_date = args.min_date
    max_date = args.max_date
    min_area = args.min_area
    max_area = args.max_area
    sensors = args.sensors
    
    xtrack_ordering(out_path=out_path,
                    num_ids=num_ids,
                    min_date=min_date,
                    max_date=max_date,
                    min_area=min_area,
                    max_area=max_area,
                    sensors=sensors)
    