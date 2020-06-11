# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 20:27:05 2020

@author: disbr007
"""
import os
import pandas as pd
import geopandas as gpd

from selection_utils.query_danco import query_footprint, count_table, pgc_ids
from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import onhand_ids

logger = create_logger(__name__, 'sh', 'DEBUG')

# Params
out_txt = r'E:\disbr007\imagery_orders\PGC_order_2020_jun09_usfs\PGC_order_2020_jun09_usfs.txt'
danco_lyr = 'index_dg'
limit = 25000
prj_dir = r'V:\pgc\data\scratch\jeff\projects\usfs'
usfs_p = os.path.join(prj_dir, r'usfs_bounds\usfs_bounds.shp')
us_state_p = r'E:\disbr007\general\US_States\tl_2017_us_state.shp'
prj = r'+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs '
noh = True

# Load USFS boundaries
logger.debug('Loading USFS boundaries...')
usfs = gpd.read_file(usfs_p)
usfs = usfs.to_crs(epsg=4326)
minx, miny, maxx, maxy = usfs.total_bounds

# Query footprint
where = 'x1 > {} AND x1 < {} AND y1 > {} and y1 < {}'.format(minx, maxx,
                                                             miny, maxy)
logger.debug('Where clause for query: {}'.format(where))

count = count_table(danco_lyr, where=where, table=True, noh=noh)
logger.debug('Count for table with where clause: {:,}'.format(count))

#%%
usfs_fps = gpd.GeoDataFrame()
offset = 0
while offset < count:
    logger.debug('Loading records: {:,} - {:,}'.format(offset, offset+limit))
    # Load footprints
    fps = query_footprint(danco_lyr, where=where, limit=limit, offset=offset, noh=noh)
    # Intersect to find USFS footprints
    logger.debug('Identifying records on USFS land...')
    slice_usfs_fps = gpd.sjoin(fps, usfs, op='within')
    logger.debug('USFS records found: {}'.format(len(slice_usfs_fps)))
    # Merge to master dataframe
    usfs_fps = pd.concat([usfs_fps, slice_usfs_fps])
    logger.debug('Total USFS records found: {}'.format(len(usfs_fps)))
    # Increase offset
    offset += limit

usfs_fps_catids = set(usfs_fps['catalogid'])
#%%
# Remove onhand IDs
# oh = onhand_ids()
# mfp_ids = pgc_ids()
# usfs_noh = [x for x in usfs_fps_catids if x not in oh]
# usfs_nmfp = [x for x in usfs_fps_catids if x not in mfp_ids]

logger.info('Writing IDs to: {}'.format(out_txt))
with open(out_txt, 'w') as src:
    src.write('\n'.join(usfs_fps_catids))

# #%%
# states = gpd.read_file(us_state_p)
# prj = r'+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs '
# states = states.to_crs(prj)
# usfs = usfs.to_crs(prj)
# usfs_fps = usfs_fps.to_crs(prj)
# #%% Plotting
# import matplotlib.pyplot as plt
# # from mpl_toolkits.basemap import Basemap
#
# plt.style.use('spy4_blank')
#
# fig, ax = plt.subplots(1,1)
#
# states.plot(color='none', edgecolor='white', linewidth=0.5, ax=ax)
# usfs.plot(color='green', edgecolor='green', alpha=0.5, ax=ax)
# usfs_fps.plot(color='red', ax=ax)
#
# minx, miny, maxx, maxy = usfs_fps.total_bounds
# pad = 0
# ax.set_xlim(minx+pad, maxx+pad)
# ax.set_ylim(miny+pad, maxy+pad)