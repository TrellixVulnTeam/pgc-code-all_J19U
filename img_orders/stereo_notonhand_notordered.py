# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import geopandas as gpd
import pandas as pd
import os

driver = 'ESRI Shapefile'

#project_path = r"C:\Users\disbr007\imagery_orders\not_onhand"

# Shapefile of not on hand stereo - from stereo_notonhand.py
noh_path = r'C:\Users\disbr007\imagery_orders\stereo_notonhand_cc20.shp'
noh = gpd.read_file(noh_path, driver=driver)
noh = noh[noh.acqdate > '2019']

# Path where text files of orders are kept
ordered_path = r'E:\disbr007\imagery_orders\ordered'
orders = [os.path.join(ordered_path, x) for x in os.listdir(ordered_path)]
ordered_ids = []
for order in orders:
    df = pd.read_csv(order, header=None)
    ids = list(df[0])
    ordered_ids += ids
    
noh_clean = noh[~noh.catalogid.isin(ordered_ids)]

out_path = r'E:\disbr007\imagery_orders\PGC_order_2019apr01_stereo_noh_2019\stereo_noh_2019.xlsx'
noh_clean.to_excel(out_path)





















