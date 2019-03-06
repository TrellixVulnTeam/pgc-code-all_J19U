# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:33:17 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

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
            

# All of Thomas' DG folders to pull most recent ids from, need to determine where cutoff in index is

dg_ftp_folder = r'Y:\private\imagery\satellite\_footprints\AGIC_footprint\DG_ftp_v5'
dg_ftp_shps = {}
# loop through all shapefiles, store filenames by date, which is suffix of filename before .shp
for filename in os.listdir(dg_ftp_folder):
    if filename.endswith('.shp'):
        ftp_num = filename.split('_')[1]
        ftp_num = int(ftp_num.strip('ftp'))
        dg_ftp_shps[ftp_num] = filename

# Read index into geopandas        
index_path = r"E:\disbr007\UserServicesRequests\pgcImageryIndexV6_2019jan12.gdb"
index = gpd.read_file(index_path, driver='OpenFileGDB', layer='pgcImageryIndexV6_2019feb04')
last_o_drive = max(list(index['O_DRIVE']))
