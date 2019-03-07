# -*- coding: utf-8 -*-
"""
Created on Thu Mar  7 09:31:11 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import os

from query_danco import query_footprint

#stereo_all = query_footprint('dg_imagery_index_stereo') # all dg stereo as df
#dg_index_cc20 = query_footprint('dg_imagery_index_all_cc20') # all dg imagery cc20 as df
#dg_stereo_catalogids = query_footprint('dg_stereo_catalogids', table=True)
dg_all = query_footprint('index_dg')

# text file containing ids, one/line to select from dg footprint
ids_path = r'C:\Users\disbr007\imagery_orders\not_onhand\stereo_ids_not_onhand.txt'
ids = []
with open(ids_path, 'r') as f:
    content = f.readlines()
    for line in content:
        ids.append(line.strip())

# Select rows from df's that are in ids list
#stereo_noh_corrected = stereo_all[stereo_all['catalogid'].isin(ids)] #only returning 12,223
#stereo_noh2 = dg_index_cc20[dg_index_cc20['catalogid'].isin(ids)]
#stereo_noh_tbl = dg_stereo_catalogids[dg_stereo_catalogids['catalogid'].isin(ids)]
stereo_noh_from_all = dg_all[dg_all['catalogid'].isin(ids)]