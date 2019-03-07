# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:33:17 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

from query_danco import stereo_noh

# IMA Ordered IDs
all_paths = [
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_1.csv",
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_2.csv"
        ]

all_ordered = []
for tbl in all_paths:
    with open(tbl, 'r') as f:
        content = f.readlines()
        content = [x.strip() for x in content] 
        for x in content:
            all_ordered.append(x)
            

## All of Thomas' DG folders to pull most recent ids from, need to determine where cutoff in index is
#dg_ftp_folder = r'Y:\private\imagery\satellite\_footprints\AGIC_footprint\DG_ftp_v5'
#dg_ftp_shps = {}
## loop through all shapefiles, store filenames by date, which is suffix of filename before .shp
#for filename in os.listdir(dg_ftp_folder):
#    if filename.endswith('.shp'):
#        ftp_num = filename.split('_')[1]
#        ftp_num = ftp_num.strip('ftp')
#        dg_ftp_shps[ftp_num] = filename

# Read index into geopandas        

#index_path = r"C:\Users\disbr007\pgc_index\pgcImageryIndexV6_2019feb04.gdb"
#index = gpd.read_file(index_path, driver='OpenFileGDB', layer='pgcImageryIndexV6_2019feb04')
#print('Index loaded into geopandas...')

index_path = r"C:\Users\disbr007\imagery_orders\not_onhand\index.txt"
index = pd.read_csv(index_path)
print("index loaded")

# For searching via Thomas' shapefiles...
#index_o_drives = list(index['O_DRIVE'])
#index_o_drives = [x.strip('DG_ftp') for x in index_o_drives if x.startswith('DG_ftp')]

index_ids = list(set(list(index['CATALOG_ID'])))

nasa_path = r"C:\Users\disbr007\imagery_orders\not_onhand\nga_inventory20190219.txt"
nasa = pd.read_csv(nasa_path)
nasa_ids = list(set(list(nasa['CATALOG_ID'])))
print('nasa loaded')

all_oh = all_ordered + index_ids + nasa_ids
all_oh = list(set(all_oh))
all_oh_out = r'C:\Users\disbr007\imagery_orders\not_onhand\all_ids_onhand.txt'
with open(all_oh_out, 'w') as all_out:
    for x in all_out:
        all_out.write('{}\n'.format(x))

stereo_noh = stereo_noh()

s_noh_ids = list(stereo_noh['catalogid'])

s_noh_remove = list(set(s_noh_ids).difference(all_oh))


txt_out_path = r'C:\Users\disbr007\imagery_orders\not_onhand\stereo_ids_not_onhand.txt'
with open(txt_out_path, 'w') as f:
    for x in s_noh_remove:
        f.write('{}\n'.format(x))



