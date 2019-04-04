# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 13:13:03 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point

def merge_gdf(gdf1, gdf2):
    gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True), crs=gdf1.crs)
    return gdf

driver = 'ESRI Shapefile'

test_poly_path = r'E:\disbr007\UserServicesRequests\Projects\1518_pfs\pfs_crrel_traverse_routes_2019.shp'

#test_poly = gpd.read_file(test_poly_path, driver=driver)
#cols = list(test_poly)
#cols.remove('geometry')

#nodes = gpd.GeoDataFrame(columns=cols)
#for i in range(len(test_poly)):
#    poly = test_poly.loc[[i]]
#    for j in list(poly.geometry.iloc[0].coords):
#        poly['pts'] = Point(j)
#        nodes = merge_gdf(nodes, poly)
#
#nodes.set_geometry('pts', inplace=True)
#nodes.drop(['geometry'], axis=1, inplace=True)
#nodes.crs = test_poly.crs
#nodes.to_file(r'E:\disbr007\UserServicesRequests\Projects\1518_pfs\3690_rennermalm_dems\project_files\nodes.shp', driver=driver)


    
    
    
test_poly = gpd.read_file(test_poly_path, driver=driver)
test_poly = test_poly[test_poly.Team == 'Rennermalm']

tester = line2pts(test_poly, 0.1)

#nodes = gpd.GeoDataFrame(columns=['pts'])
#for i in np.arange(0.0, 1.0, 0.1):
#    node = gpd.GeoDataFrame(columns=['pts'])
#    pt = test_poly.geometry.interpolate(i, normalized=True)
#    print(i, pt)
#    node['pts'] = pt
#    nodes = merge_gdf(nodes, node)
#
#nodes.set_geometry('pts', inplace=True)
##nodes.drop(['geometry'], axis=1, inplace=True)
#nodes.crs = test_poly.crs
nodes.to_file(r'E:\disbr007\UserServicesRequests\Projects\1518_pfs\3690_rennermalm_dems\project_files\nodes.shp', driver=driver)