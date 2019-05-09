# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:03:31 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
from fiona.crs import from_epsg, from_string

xtrack_path = r"C:\Users\disbr007\scratch\xtrack_test.shp"
utm_zone_path = r"C:\Users\disbr007\scratch\UTM_Zone_Boundaries\UTM_Zone_Boundaries.shp"

driver = 'ESRI Shapefile'
xtrack = gpd.read_file(xtrack_path, driver=driver)
utm_zones = gpd.read_file(utm_zone_path, driver=driver)

xtrack['centroid'] = xtrack.centroid
xtrack.set_geometry('centroid', inplace=True)

# Locate region of centroid
xtrack = gpd.sjoin(xtrack, utm_zones, how='left', op='within')
xtrack.drop('centroid', axis=1, inplace=True)
xtrack.set_geometry('geometry', inplace=True)
cols = list(xtrack)
cols.append('sqkm')

xtrack_recombine = gpd.GeoDataFrame(columns=cols)

utm_dfs = {}
for utm_zone, df in xtrack.groupby('Zone_Hemi'):
    zone = utm_zone.split(',')[0]
    hemi = utm_zone.split(',')[1]
    if hemi == 's':
        proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
    elif 'n':
        proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
    
    source_crs = df.crs
    df.geometry = df.geometry.to_crs(proj4)
    df.crs = from_string(proj4)
    df['sqkm'] = df.geometry.area / 10**6
    df.geometry = df.geometry.to_crs(source_crs)
    df.crs = source_crs
    utm_dfs[utm_zone] = df
    xtrack_recombine = pd.concat([xtrack_recombine, df])
    
def utm_area_calc(gdf):
    for utm_zone, gdf in xtrack.groupby('Zone_Hemi'):
    zone = utm_zone.split(',')[0]
    hemi = utm_zone.split(',')[1]
    if hemi == 's':
        proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
    elif 'n':
        proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
    
    source_crs = gdf.crs
    gdf.geometry = gdf.geometry.to_crs(proj4)
    gdf.crs = from_string(proj4)
    gdf['sqkm'] = gdf.geometry.area / 10**6
    gdf.geometry = gdf.geometry.to_crs(source_crs)
    gdf.crs = source_crs
    utm_dfs[utm_zone] = df
    xtrack_recombine = pd.concat([xtrack_recombine, gdf])