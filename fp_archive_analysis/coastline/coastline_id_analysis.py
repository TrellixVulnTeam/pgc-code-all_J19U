# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 08:33:29 2019

@author: disbr007
Analysis of DG and MFP coastline candidate ids. Compares
onhand and not on hand, creates list of 
ids to order for coastline, ids to get from NASA
and generates geocells to task for 
additional collection.
"""

import geopandas as gpd

from id_parse_utils import read_ids


#### Load candidate footprints
## Paths
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
dg_cand_p = 'dg_global_coastline_candidates'
mfp_cand_p = 'mfp_global_coastline_candidates'
nasa_cand_p = 'nasa_global_coastline_candidates'
## Load
driver = 'OpenFileGDB'
dg_cand = gpd.read_file(gdb, driver=driver, layer=dg_cand_p)
mfp_cand = gpd.read_file(gdb, driver=driver, layer=mfp_cand_p)
#nasa_cand = gpd.read_file(gdb, driver=driver, layer=nasa_cand_p)


#### Determine ids to order
## Get ids
dg_cand_ids = set(dg_cand['catalogid'].unique())
mfp_cand_ids = set(mfp_cand['catalog_id'].unique())
#nasa_cand_ids = set(nasa_cand['CATALOG_ID'].unique())
order_ids = dg_cand_ids - mfp_cand_ids

## Get footprint for order
order = dg_cand[dg_cand['catalogid'].isin(order_ids)]

