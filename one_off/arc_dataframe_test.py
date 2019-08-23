# -*- coding: utf-8 -*-
"""
Created on Thu Aug 22 11:49:50 2019

@author: disbr007
"""

import arcpy
from arcgis.features import SpatialDataFrame, GeoAccessor
from arcgis.geometry import Geometry

import pandas as pd
import geopandas as gpd

#
gdf_p = r'C:\Users\disbr007\projects\coastline\mfp_test_density.shp'
#gdb = r'C:\Users\disbr007\projects\coastline\coast.gdb'
#lyr = r'nasa_global_coastline_candidates'
#gdf_p = r'C:\Users\disbr007\projects\coastline\dg_global_coastline_candidates_seaice.shp'
print('loading gdf')
#gdf = gpd.read_file(gdb, layer=lyr, driver='OpenFileGDB')
gdf = gpd.read_file(gdf_p, driver='ESRI Shapefile')

geoms = gdf.geometry

df = pd.DataFrame.spatial()

#sdf = SpatialDataFrame.from_dict(json)

print('getting geoms')
arcgis_polys = [Geometry.from_shapely(i) for i in geoms]


print('creating sdf')
sdf = SpatialDataFrame(data=df, geometry=arcgis_polys)
sdf.spatial.set_geometry(arcgis_polys)
#
out_p = r'C:\Users\disbr007\projects\coastline\coast.gdb\sdf'
print('writing sdf to fc')
sdf.spatial.to_featureclass(out_p)
##sdf.to_featureclass(gdb, )
#
##ga = GeoAccessor(gdf)
##ga.set_geometry('geometry')
##ga.to_featureclass(gdb)

