# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 10:08:31 2019

@author: disbr007
"""

import re
import os
from pprint import pprint

import geopandas as gpd
import pandas as pd

from clip2shp_bounds import warp_rasters
from id_parse_utils import write_ids


# Params
PRJ_DIR = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056\prj_files'
AOI_PATH = os.path.join(PRJ_DIR, r'BITE_buffers.shp')
IDS_PATH = os.path.join(PRJ_DIR, r'BITE_ids.txt')
MFP_SEL = os.path.join(PRJ_DIR, r'mfp_subset_selection.shp')


aois_master = {}
with open(IDS_PATH, 'r') as src:
    content = src.read()
    aois = content.split('\n\n')
    for aoi in aois:
        aoi_num = re.findall(r"AOI [0-9]+", aoi)[0].split(' ')[1]
        # print(aoi_num)
        cids = aoi.split('\nCatalog IDs:')[1]
        cids = cids.split('\nArea')[0]
        cids = cids.split(',')
        cids = [c.strip(' ') for c in cids]
        aois_master[aoi_num] = cids
        
aois_m = []
cids_m = []
for aoi, cids in aois_master.items():
    print(aoi)
    # print(cids)
    for c in cids:
        # print(c)
        aois_m.append(aoi)
        cids_m.append(c)
        
write_ids(cids_m, os.path.join(PRJ_DIR, 'selected_ids.txt'))

aois_ids = pd.DataFrame({'AOI': aois_m, 'ID':cids_m})
aois_shp = gpd.read_file(AOI_PATH)
aois_shp['subfolder'] = aois_shp['subfolder'].astype(str)

master = aois_ids.merge(aois_shp, how='left', left_on='AOI', right_on='subfolder')

mfp_selection = gpd.read_file(MFP_SEL)
master_selection = mfp_selection.merge(master, 
                                       how='left', 
                                       left_on='catalog_id', 
                                       right_on='ID')
master_selection = master_selection.drop_duplicates(subset=['scene_id'])
master_selection = master_selection.set_geometry('geometry_x')
master_selection = master_selection.drop(columns=['geometry_y'])

master_selection.crs = mfp_selection.crs
master_selection.to_file(os.path.join(PRJ_DIR, 'mfp_scene_ids.shp'))


