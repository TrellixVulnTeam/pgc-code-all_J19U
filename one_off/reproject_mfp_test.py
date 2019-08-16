# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 10:21:45 2019

@author: disbr007
"""

import geopandas as gpd


coast_p = r'C:\Users\disbr007\projects\coastline\scratch\greenland_coast.shp'
coast = gpd.read_file(coast_p, driver='ESRI Shapefile')


mfp_p = r'C:\pgc_index\pgcImageryIndexV6_2019jun06_LAT30_LON60.gdb'
mfp = gpd.read_file(mfp_p, driver='OpenFileGDB', layer='pgcImageryIndexV6_2019jun06_LAT0_LON60')

print('Coast crs: {}'.format(coast.crs))
print('MFP crs: {}'.format(mfp.crs))

if coast.crs != mfp.crs:
    mfp.to_crs(coast.crs, inplace=True)

print('Coast crs: {}'.format(coast.crs))
print('MFP crs: {}'.format(mfp.crs))