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
# out_path = r''
# num_ids = 40_000 # Desired number of IDs
# sensors = ['WV01', 'WV02', 'WV03']

# min_date = '2019-04-23'
# max_date = None

# max_area = None # Max overlap area to include
# min_area = 1000 # Min overlap area to include


def xtrack_ordering(out_path, num_ids, min_date, max_date,
                    min_area, max_area, sensors, noh, project):
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
    if project:
        where = check_where(where)
        where += """project IN ({})""".format(str(project)[1:-1])
    
    # Count the number of records returned by the where sql query
    logger.info('Where clause for selection: {}'.format(where))
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
            if noh:
                # Remove onhand
                logger.info('Removing on hand ids...')
                oh_ids = set(mfp_ids())
                xt_chunk = xt_chunk[(~xt_chunk['catalogid1'].isin(oh_ids)) & (~xt_chunk['catalogid2'].isin(oh_ids))]
                logger.info('Remaining records: {}'.format(len(xt_chunk)))
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
    logger.info('Records before removing onhand: {}'.format(len(xt_area)))
    
    if noh:
        # Remove onhand
        logger.info('Removing on hand ids...')
        oh_ids = set(mfp_ids())
        xt_area = xt_area[(~xt_area['catalogid1'].isin(oh_ids)) & (~xt_area['catalogid2'].isin(oh_ids))]
    
    logger.info('Summary of all matching footprints:\n{}'.format(xt_area.describe()))
    # Stack catalogid1 and catalogid2 with area col
    all_ids = pd.concat([xt_area[['catalogid1', area_col]], xt_area[['catalogid2', area_col]]])
    
    if min_area or max_area:
        # Sort by area, max first, then get first n records
        all_ids.sort_values(by=area_col, ascending=False, inplace=True)
    else:
        # Sort by percent overlap
        all_ids.sort_values(by='perc_ovlp', ascending=False)
        
    logger.info('Selecting first {} IDs...'.format(num_ids))
    selected_records = xt_area.iloc[0:num_ids]
    # Remove any duplicates
    selected_ids = set(list(selected_records['catalogid1']) + list(selected_records['catalogid2']))
    
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
    parser.add_argument('-noh', '--not_on_hand', action='store_true',
                        help='Use this flag to only return records not on hand.')
    parser.add_argument('--project', nargs='+',
                        help='Projects to include (i.e. regions): EarthDEM ArcticDEM REMA')
    
    args = parser.parse_args()
    
    out_path = args.out_path
    num_ids = args.num_ids
    min_date = args.min_date
    max_date = args.max_date
    min_area = args.min_area
    max_area = args.max_area
    sensors = args.sensors
    noh = args.not_on_hand
    project = args.project
    
    xtrack_ordering(out_path=out_path,
                    num_ids=num_ids,
                    min_date=min_date,
                    max_date=max_date,
                    min_area=min_area,
                    max_area=max_area,
                    sensors=sensors,
                    noh=noh,
                    project=project)
    