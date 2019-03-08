# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 11:58:03 2019

@author: disbr007
Determine the number of unique cross track catalog ids not ordered, by month, overlap area, sensor
"""

import geopandas as gpd
import pandas as pd
import id_parse_utils

## Xtrack Data prep
# Load crosstrack database
xtrack_path = r"C:\Users\disbr007\imagery\dg_cross_track_2019jan09_deliv.gdb"
xtrack = gpd.read_file(xtrack_path, driver='OpenFileGDB', layer=1)

# Split into '1' and '2' xtrack dataframes - keep overlap area ids
# Drop geometry and unncessary columns
xtrack1_cols = ['catalogid1', 'acqdate1', 'sqkm']
xtrack2_cols = ['catalogid2', 'acqdate2', 'sqkm']

xtrack1 = xtrack[xtrack1_cols]
xtrack2 = xtrack[xtrack2_cols]
del xtrack
# Stack '1' and '2' xtrack dataframes
col_rename = {
        'catalogid1': 'catalogid',
        'catalogid2': 'catalogid',
        'acqdate1': 'acqdate',
        'acqdate2': 'acqdate'
        }
xtrack1.rename(index=str, columns=col_rename, inplace=True)
xtrack2.rename(index=str, columns=col_rename, inplace=True)

xtrack = pd.concat([xtrack1, xtrack2])

# Remove duplicate ids
xtrack.drop_duplicates('catalogid', keep='first', inplace=True)

# Determine platform of id
# Join to dg_all

## Determine 'onhand' (PGC, NASA, ordered)
onhand_ids_path = r'C:/Users/disbr007/imagery_orders/not_onhand/onhand_ids.txt'

## Remove onhand ids from xtrack ids

## Write to excel: monthly unique strips, w/ overlap area, and sensor, and totals

