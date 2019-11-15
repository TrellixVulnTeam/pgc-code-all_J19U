# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 10:10:56 2019

@author: disbr007
"""

import os

import geopandas as gpd


prj_dir = r'E:\disbr007\UserServicesRequests\Projects\akhan'
aoi_p = os.path.join(prj_dir, 'aoi_pts.shp')
fp_p = os.path.join(prj_dir, 'fp_test.shp')

aoi = gpd.read_file(aoi_p)
fp = gpd.read_file(fp_p)

sj = gpd.sjoin(aoi, fp, how='left')
print(len(sj))
print(len(sj.catalogid.unique()))
sj.drop_duplicates(subset=['catalogid'], inplace=True)
print(len(sj))
print(len(sj.catalogid.unique()))
print(list(sj))
sj.drop(columns=list(aoi), inplace=True)
print(list(sj))