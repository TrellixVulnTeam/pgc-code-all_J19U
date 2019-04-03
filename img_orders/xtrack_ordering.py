# -*- coding: utf-8 -*-
"""
Created on Thu Mar 21 09:57:17 2019

@author: disbr007

xtrack not on hand ordering
"""

import geopandas as gpd
import pandas as pd

xtrack_shp = r'C:\Users\disbr007\imagery\xtrack_onhand\xtrack_onhand.shp'
xtrack = gpd.read_file(xtrack_shp, driver='ESRI Shapefile')

xtrack1k = xtrack[xtrack['sqkm'] >= 1000.0]

xtrack1k_noh1 = xtrack1k[xtrack1k['id1_onhand'] == 0]
xtrack1k_noh2 = xtrack1k[xtrack1k['id2_onhand'] == 0]

xtrack1k_noh = []
for e in list(xtrack1k_noh1.catalogid1):
    xtrack1k_noh.append(e)
    
for e in list(xtrack1k_noh2.catalogid2):
    xtrack1k_noh.append(e)

xtrack1k_noh_wv3 = [x for x in xtrack1k_noh if x.startswith('104')]

out_txt = r'C:\Users\disbr007\imagery\xtrack_onhand\xtrack_noh_1k_wv03_2019march21.txt'
with open(out_txt, 'w') as f:
    for item in xtrack1k_noh_wv3:
        f.write('{}\n'.format(item))

written_ids = []
with open(out_txt, 'r') as f:
    content = f.readlines()
    for i in content:
        written_ids.append(i)
