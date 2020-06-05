#%% Modules
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 15:28:11 2020

@author: disbr007
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 13:08:08 2020

@author: disbr007
"""
# Suppress geopandas crs FutureWarning
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import argparse
import collections
import os
import sys

import pandas as pd
import geopandas as gpd
# from tqdm import tqdm

from misc_utils.utm_area_calc import area_calc

from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import write_ids, get_platform_code, ordered_ids
from selection_utils.query_danco import query_footprint, count_table

# Turn off pandas warning
pd.options.mode.chained_assignment = None 

#%% Set up
# Inputs
num_ids = 60_000 # Desired number of IDs
remove_onhand = True
combo_sensors = False
# sensors = ['WV01', 'WV02', 'WV03']
sensors = ['WV03']
min_date = '2018-07-00'
max_date = '2019-12-32'
orderby = 'perc_ovlp'
where = "(project = 'EarthDEM')" # AND (region_name IN ('Mexico and Caribbean', 'CONUS', 'Great Lakes'))"
# aoi_path = r'E:\disbr007\general\US_States\us_no_AK.shp'
aoi_path = None
out_path = r'E:\disbr007\imagery_orders\NASA_order_2020jun04_global_xtrack_2018jan01_2019dec31\NASA_order_2020jun04_global_xtrack_2018jul01_2019dec31.txt'


logger = create_logger(__name__, 'sh', 'DEBUG')

# Check for existence of aoi and out_path directory
# if not os.path.exists(aoi_path):
    # logger.error('AOI path does not exist: {}'.aoi_path)
    # sys.exit()
if not os.path.exists(os.path.dirname(out_path)):
    logger.warning('Out directory does not exist, will be created: {}'.format(out_path))

if sensors:
    sensor_where = ''
    for sensor in sensors:
        if sensor_where:
            sensor_where += ' OR '
        sensor_where += """(catalogid1 LIKE '{0}%%' OR catalogid2 LIKE '{0}%%')""".format(get_platform_code(sensor))
    if where:
        where += " AND "
    where += '({})'.format(sensor_where)
if min_date:
    if where:
        where += " AND "
    where += "(acqdate1 >= '{}')".format(min_date)
if max_date:
    if where:
        where += " AND "
    where += "(acqdate1 <= '{}')".format(max_date)
if not combo_sensors:
    if where:
        where += " AND "
    where += "(SUBSTRING(catalogid1, 1, 3) = SUBSTRING(catalogid2, 1, 3))"
logger.debug('SQL where: {}'.format(where))

if aoi_path:
    aoi = gpd.read_file(aoi_path)

# Params
xtrack_tbl = 'dg_imagery_index_xtrack_cc20'
chunk_size = 50_000
area_col = 'area_sqkm'
columns = ['catalogid1', 'catalogid2', 'region_name', 'pairname', 'acqdate1']

table_total = count_table(xtrack_tbl, where=where)
logger.info('Total table size with query: {:,}'.format(table_total))
# table_total = 20000

# Get all onhand ids
oh_ids = set(ordered_ids(update=False))

#%% Iterate
# Iterate chunks of table, calculating area and adding id1, id2, area to dictionary
all_ids = []
limit = chunk_size
offset = 0
while offset < table_total:
    # Load chunk
    logger.info('Loading chunk: {:,} - {:,}'.format(offset, limit+offset))
    chunk = query_footprint(xtrack_tbl, columns=columns,
                            orderby=orderby, orderby_asc=False, 
                            where=where, limit=limit, offset=offset,
                            dryrun=False)

    # Remove records where both IDs are onhand
    logger.info('Dropping records where both IDs are on onhand...')
    chunk = chunk[~((chunk['catalogid1'].isin(oh_ids)) & (chunk['catalogid2'].isin(oh_ids)))]
    logger.info('Remaining records: {:,}'.format(len(chunk)))

    # Find only IDs in AOI if provided
    if aoi_path:
        logger.info('Finding IDs in AOI...')
        if aoi.crs != chunk.crs:
            aoi = aoi.to_crs(chunk.crs)
        chunk_cols = list(chunk)
        chunk = gpd.sjoin(chunk, aoi, how='inner')
        chunk = chunk[chunk_cols]
        # TODO: Confirm if this is needed, does an 'inner' sjoin leave duplicates?
        chunk.drop_duplicates(subset='pairname')
        logger.info('Remaining records: {:,}'.format(len(chunk)))

    # Calculate area for chunk
    logger.info('Calculating area...')
    chunk = area_calc(chunk, area_col=area_col)

    # Add tuple of (catid1_catid2, area) now done above: (if both ids are not already on hand )
    # If only one is on hand, it is removed later and the noh id is added to the final list
    chunk_ids = [("{}_{}".format(c1, c2), area) for c1, c2, area in zip(list(chunk['catalogid1']),
                                                                        list(chunk['catalogid2']),
                                                                        list(chunk[area_col]))]

    logger.info('IDs matching criteria from chunk: {:,}\n'.format(len(chunk_ids)))
    all_ids.extend(chunk_ids)

    # Increase offset
    offset += limit

#%% Combining
# Remove any duplicates from different pairs of cid1+cid2, cid1+cid3, etc.
all_ids = list(set(all_ids))

# Sort by area
all_ids_dict = collections.OrderedDict(all_ids)
all_ids_dict = sorted(all_ids_dict.items(), key=lambda kv: kv[1], reverse=True)

# Create final list
final_ids = []

# Check if either ID is on hand, if not add
# while len(final_ids) < num_ids:
logger.info('Records meeting criteria where both IDs are not onhand: {}'.format(len(all_ids_dict)))
logger.info('Removing any onhand ids...')
for c1_c2, area in all_ids_dict:
    c1, c2 = c1_c2.split('_')
    if remove_onhand:
        if c1 not in oh_ids and c1 not in final_ids:
            final_ids.append(c1)
        if c2 not in oh_ids and c2 not in final_ids:
            final_ids.append(c2)
    else:
        final_ids.append(c1)
        final_ids.append(c2)
logger.info('Total IDs matching criteria: {:,}'.format(len(final_ids)))
logger.info('Selecting {:,} IDs...'.format(num_ids))
selected_final_ids = final_ids[0:num_ids]

#%% Write
if not os.path.exists(os.path.dirname(out_path)):
    os.makedirs(os.path.dirname(out_path))
logger.info('Writing {:,} IDs to: {}'.format(len(selected_final_ids), out_path))
write_ids(selected_final_ids, out_path)
