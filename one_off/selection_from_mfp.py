# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 11:51:05 2019

@author: disbr007
Select from master footprint based on latitude and subset results
"""

import fiona, os, tqdm
from pprint import pprint
import geopandas as gpd
import pandas as pd
from select_ids_pgc_index import mfp_subset
from gpd_utils import merge_gdfs


aoi_p = r'E:\disbr007\UserServicesRequests\Projects\jmauss\deliv_temp\aoi_poly.shp'
aoi = gpd.read_file(aoi_p, driver='ESRI Shapefile')

dfs = mfp_subset(75, 80)

all_matches = []
for layer in tqdm.tqdm(dfs):
    if aoi.crs != layer.crs:
        aoi.to_crs(layer.crs, inplace=True)
    matches = gpd.sjoin(layer, aoi)
    all_matches.append(matches)
    
init_selection = merge_gdfs(all_matches)
init_selection['acq_time'] = pd.to_datetime(init_selection['acq_time'])

selection = init_selection[(init_selection['acq_time'] > '2012-03') & (init_selection['acq_time'] < '2012-05')]

