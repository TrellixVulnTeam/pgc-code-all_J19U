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
            
## Read index into geopandas
#index_path = r"C:\Users\disbr007\pgc_index\pgcImageryIndexV6_2019feb04.gdb"
#index = gpd.read_file(index_path, driver='OpenFileGDB', layer='pgcImageryIndexV6_2019feb04')
# Read text version of master footprint into pandas
index_path = r"C:\Users\disbr007\imagery_orders\not_onhand\index.txt"
index = pd.read_csv(index_path)
print('index loaded')
# List of unique ids in the index
index_ids = list(set(list(index['CATALOG_ID'])))

# Read text version of nasa database into pandas
nasa_path = r"C:\Users\disbr007\imagery_orders\not_onhand\nga_inventory20190219.txt"
nasa = pd.read_csv(nasa_path)
# List unique ids in nasa db
nasa_ids = list(set(list(nasa['CATALOG_ID'])))
print('nasa loaded')

# Combine all ordered, pgc index and nasa index ids
all_oh = all_ordered + index_ids + nasa_ids
# Get unique ids of combined list
all_oh = list(set(all_oh))

# Write list of unique ids "onhand" to file
all_oh_out = r'C:\Users\disbr007\imagery_orders\not_onhand\all_ids_onhand.txt'
with open(all_oh_out, 'w') as all_out:
    for x in all_oh:
        all_out.write('{}\n'.format(x))

# Get stereo not onhand from 'stereo_not_onhand_left' and 'stereo_not_onhand_right'
stereo_noh = stereo_noh()
# List ids in stereo not_on_hand
stereo_noh_ids = list(stereo_noh['catalogid'])

# Remove all on hand ids from list of not on hand -> this theoretically shouldn't be necessary but is for some reason - talk to CLaire
stereo_noh_clean = list(set(stereo_noh_ids).difference(all_oh))

# Write stereo ids not on hand to list
txt_out_path = r'C:\Users\disbr007\imagery_orders\not_onhand\stereo_ids_not_onhand.txt'
with open(txt_out_path, 'w') as f:
    for x in stereo_noh_clean:
        f.write('{}\n'.format(x))



