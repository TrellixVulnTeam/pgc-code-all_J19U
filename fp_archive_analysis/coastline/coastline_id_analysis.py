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
gdb = r'C:\Users\disbr007\projects\coastline\coast.gdb'
oh_cand_p = 'oh_final_candidates'
dg_cand_p = 'dg_final_candidates'

## Load
driver = 'OpenFileGDB'
dg_cand = gpd.read_file(gdb, driver=driver, layer=dg_cand_p)
oh_cand = gpd.read_file(gdb, driver=driver, layer=oh_cand_p)


#### Determine ids to order
## Get ids
dg_cand_ids = set(dg_cand['catalogid'].unique())
oh_cand_ids = set(oh_cand['CATALOG_ID'].unique())
order_ids = dg_cand_ids - oh_cand_ids

perc_oh = (len(oh_cand_ids) / len(dg_cand_ids)) * 100
print("We have {:,} IDs, out of {:,} = {:.0f}%".format(len(oh_cand_ids), len(dg_cand_ids), perc_oh))

print("ID's we can order: {:,}".format(len(order_ids)))

processed_p = r'C:\Users\disbr007\projects\coastline\pickles\ArcticCoast_v1.3_selection_sceneids.txt'
processed_scids = set(read_ids(processed_p))
oh_scids = set(oh_cand['SCENE_ID'])

print("We have processed {:,} scene ID's, out of {:,} = {:.0f}%".format(len(processed_scids), len(oh_scids),
      (len(processed_scids)/len(oh_scids))*100))

