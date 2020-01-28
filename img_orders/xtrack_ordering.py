# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 13:08:08 2020

@author: disbr007
"""

import os

import pandas as pd

from selection_utils.query_danco import query_footprint, count_table
from misc_utils.logging_utils import create_logger
from misc_utils.utm_area_calc import area_calc
from misc_utils.id_parse_utils import write_ids, get_platform, get_platform_code


# INPUTS
OUTPATH = r''
NUM_IDS = 40_000 # Desired number of IDs
SENSORS = ['WV01', 'WV02', 'WV03']

MIN_YEAR = '2019-04-23'
MAX_YEAR = None

MAX_AREA = 1000 # Max overlap area to include
MIN_AREA = 500 # Min overlap area to include
REMOVE_MFP = True

REGION = '' # EarthDEM region to include **NOT IMPLEMENTED**


def check_where(where):
    if where:
        where += ' AND '
    return where

# Parameters
area_col = 'sqkm_utm'

logger = create_logger(os.path.basename(__file__), 'sh',
                       handler_level='DEBUG')

# Load footprints in chunks to avoid long load time
# Xtrack table name
xtrack_name = 'dg_imagery_index_xtrack_cc20'
# Columns to load
cols = ['objectid', 'catalogid1', 'catalogid2', 'acqdate1', 'pairname']

# Build where clause
where = ""
if MIN_YEAR:
    where = check_where(where)
    where += "(acqdate1 > '{}')".format(MIN_YEAR)
if MAX_YEAR:
    where = check_where(where)
    where += "(acqdate1 < '{}'')".format(MAX_YEAR)
# Add platforms to where, there are no platform fields in the xtrack table
# so using first three digits of catalogid
sensor_where = ''
for sensor in SENSORS:
    if sensor_where:
        sensor_where += ' OR '
    sensor_where += """ 
                    (catalogid1 LIKE {0}% OR catalogid2 LIKE {0}%)
                    """.format(get_platform_code(sensor))
where += ' AND ({})'.format(sensor_where)

# Count the number of records returned by the where sql query
xt_size = count_table(xtrack_name, columns=[cols[0]], where=where)

chunksize = 100_000
prev_x = 0
xt_chunks = [] # list to store dataframe chunks
for x in range(0, xt_size, 100000):
    if x == 0:
        continue
    logger.info('Loading {} chunk: {} - {}'.format(xtrack_name, prev_x, x))
    # Add objectid range to sql clause
    where += """ AND (objectid > {} AND objectid < {})""".format(prev_x, x)
    xt_chunk = query_footprint(xtrack_name, 
                                where="objectid > {} AND objectid < {}".format(prev_x, x),
                                columns=cols)

    # Checking that loading chunks is working
    # logger.info('Max objectid in loaded chunk: {:,}'.format(xt_chunk['objectid'].max()))

    # Calculate UTM area
    # TODO: Rewrite this to be an apply function
    logging.info('Calculating utm area on chunk...'))
    xt_chunk = area_calc(xt_chunk, area_col=area_col)
    xt_chunk = xt_chunk[(xt_chunk[area_col] > MIN_AREA) & (xt_chunk[area_col] < MAX_AREA)]
    xt_chunks.append(xt_chunk)
    
    prev_x = x
    
    
xt_area = pd.concat(xt_chunks)

# Sort by area then get first n records
xt_area.sort_values(by=area_col, inplace=True)

selection = xt_area[0:NUM_IDS]

unique_ids = []
for i, row in selection.iterrows():
    id1 = row['catalogid1']
    id2 = row['catalogid2']
    if id1 not in unique_ids:
        unique_ids.append(id1)
    if id2 not in unique_ids:
        unique_ids.append(id2)
    
    unique_count = len(set(unique_ids))
    
    if unique_count >= NUM_IDS:
        break


selected_ids = set(unique_ids)

# write_ids(selected_ids, )    