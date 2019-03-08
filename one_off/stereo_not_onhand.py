# -*- coding: utf-8 -*-
"""
Created on Thu Mar  7 09:31:11 2019

@author: disbr007
Exports shapefile of selected IDs from specified danco layer
"""

import pandas as pd
import geopandas as gpd
import os

from query_danco import query_footprint

def read_ids(txt_file):
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            ids.append(line.strip())
    return ids
#stereo_all = query_footprint('dg_imagery_index_stereo') # all dg stereo as df
#dg_index_cc20 = query_footprint('dg_imagery_index_all_cc20') # all dg imagery cc20 as df
#dg_stereo_catalogids = query_footprint('dg_stereo_catalogids', table=True)
dg_all = query_footprint('index_dg') # entire dg index

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
stereo_noh_from_all_cc20 = stereo_noh_from_all[stereo_noh_from_all.cloudcover <= 20]
stereo_noh_from_all_cc20 = stereo_noh_from_all_cc20[stereo_noh_from_all_cc20.acqdate < '2019-01-01']

excel_path = r'E:\disbr007\imagery_orders\PGC_order_2019march08_intrack_not_onhand_thru_EOY2018\intrack_not_onhand_thru_EOY2018_master.xlsx'
excel_writer = pd.ExcelWriter(excel_path)
stereo_noh_from_all_cc20.to_excel(excel_writer, index=True)
excel_writer.save()
