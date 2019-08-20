# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 10:54:27 2019

@author: disbr007
Merges the MFP and NASA coastline candidates to create an
'onhand' candidate footprint.
"""

import geopandas as gpd
import pandas as pd
import os, logging, sys


#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

## Paths
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
nasa_p = r'nasa_global_coastline_candidates_seaice'
mfp_p = r'mfp_global_coastline_candidates_seaice'
# Outpath
out_dir = r'C:\Users\disbr007\projects\coastline'
out_name = 'onhand_candidates_seaice.shp'
out_path = os.path.join(out_dir, out_name)

## Load data
logger.info('Loading data...')
nasa = gpd.read_file(gdb, layer=nasa_p, driver='OpenFileGDB')
mfp = gpd.read_file(gdb, layer=mfp_p, driver='OpenFileGDB')
# Add source
nasa['source'] = 'nasa'
mfp['source'] = 'pgc'

## Rename columns
nasa_rename = {col:col.lower() for col in list(nasa)}
nasa.rename(columns=nasa_rename, inplace=True)


## Keep only common columns
keep_cols = [x for x in list(mfp) if x in list(nasa)]
nasa = nasa[keep_cols]
mfp = mfp[keep_cols]


## Merge
logger.info('Merging nasa and mfp...')
onhand = pd.concat(mfp, nasa)
# Remove duplicate scene IDs, keeping the first, which should be pgc
onhand.drop_duplicates(subset=['scene_id'], keep='first', inplace=True)


## Write
logger.info('Writing to file {}'.format(out_path))
onhand.to_file(out_path, driver='ESRI Shapefile')