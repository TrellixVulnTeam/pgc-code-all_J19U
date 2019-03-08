# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 11:58:03 2019

@author: disbr007
Determine the number of unique cross track catalog ids not ordered, by month, overlap area, sensor
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import sys

sys.path.insert(0, r'C:\code\misc_utils')
import id_parse_utils

## Xtrack data prep
# Load crosstrack database
xtrack_path = r"C:\Users\disbr007\imagery\dg_cross_track_2019jan09_deliv.gdb"
xtrack = gpd.read_file(xtrack_path, driver='OpenFileGDB', layer=1)
print('xtrack db loaded into geopandas')

# Split into '1' and '2' xtrack dataframes - keep overlap area ids in both
# Drop geometry and other unncessary columns
xtrack1_cols = ['catalogid1', 'acqdate1', 'sqkm']
xtrack2_cols = ['catalogid2', 'acqdate2', 'sqkm']
xtrack1 = xtrack[xtrack1_cols]
xtrack2 = xtrack[xtrack2_cols]
del xtrack

# Stack '1' and '2' xtrack dataframes
# Rename columns for stacking
col_rename = {
        'catalogid1': 'catalogid',
        'catalogid2': 'catalogid',
        'acqdate1': 'acqdate',
        'acqdate2': 'acqdate'
        }
xtrack1.rename(index=str, columns=col_rename, inplace=True)
xtrack2.rename(index=str, columns=col_rename, inplace=True)
# Stack
xtrack = pd.concat([xtrack1, xtrack2])

# Remove duplicate ids, keeping largest area id
xtrack.sort_values(by=['sqkm'])
xtrack.drop_duplicates('catalogid', keep='first', inplace=True)

# Determine platform of id
platform_code = {
        '101': 'QB02',
        '102': 'WV01',
        '103': 'WV02',
        '104': 'WV03',
        '105': 'GE01',
        '200': 'IK01'
        }

# Use first three characters of catalogid to determine platform
xtrack['platform'] = xtrack['catalogid'].str.slice(0,3).map(platform_code)


## Determine 'onhand' (PGC, NASA, ordered)
onhand_ids_path = r'C:/Users/disbr007/imagery_orders/not_onhand/onhand_ids.txt'
oh_ids = []
with open(onhand_ids_path, 'r') as f:
    content = f.readlines()
    for line in content:
        oh_ids.append(line.strip())

## Remove onhand ids from xtrack ids
#xtrack_noh = xtrack[~xtrack.catalogid.isin(oh_ids)]
#xtrack_noh = xtrack_noh.set_index(pd.to_datetime(xtrack_noh['acqdate']))

# Determine xtrack onhand
#xtrack_oh = xtrack[xtrack.catalogid.isin(oh_ids)]
xtrack['onhand'] = xtrack['catalogid'].isin(oh_ids)
xtrack = xtrack.set_index(pd.to_datetime(xtrack['acqdate']))

## Monthly grouping
aggregation = {
        'catalogid': 'nunique',
        'sqkm': 'sum'
        }
monthly_xtrack = xtrack.groupby([pd.Grouper(freq='M'), 'platform', 'onhand']).agg(aggregation)
monthly_xtrack = monthly_xtrack.unstack(level=-1) # Unstack 'onhand' column
monthly_xtrack = monthly_xtrack.unstack(level=-1) # Unstack platform column

# Rename to reflect aggregation
col_rename = {
        'catalogid': 'Unique_Strips',
        'sqkm': 'Total_Area'}
monthly_xtrack.rename(index=str, columns=col_rename, inplace=True)

## Write to excel: monthly unique strips, w/ overlap area, and sensor, and totals
excel_path = r'C:\Users\disbr007\imagery\not_onhand\xtrack.xlsx'
excel_writer = pd.ExcelWriter(excel_path)
monthly_xtrack.to_excel(excel_writer, index=True)
excel_writer.save()