# -*- coding: utf-8 -*-
"""
Created on Thu Aug  1 16:53:16 2019

@author: disbr007
"""

import timeit
#import arcpy
#import geopandas as gpd

#shp_path = 'C:\temp\\speed_test.gdb'
gpd_setup = '''
import geopandas as gpd
import os
'''
gpd_stmt = r"""
shp_path = r'C:\temp\speed_test.gdb'
shp = gpd.read_file(shp_path, driver='OpenFileGDB', layer=0)
shp = None
"""

print(timeit.timeit(stmt=gpd_stmt, setup=gpd_setup, number=1000))


#shp_path = 'C:\temp\\speed_test.gdb'
gpd_setup1 = '''
import geopandas as gpd
import os
'''
gpd_stmt1 = r"""
shp_path = r'C:\temp\fp_1k.shp'
shp = gpd.read_file(shp_path, driver='ESRI Shapefile')
shp = None
"""

print(timeit.timeit(stmt=gpd_stmt1, setup=gpd_setup1, number=1000))


#arcpy_setup = 'import arcpy'
#arcpy_stmt = r'''
#shp_path = r'C:\temp\speed_test.gdb\fp_1k'
#shp = arcpy.MakeFeatureLayer_management(shp_path)
#shp = None
#'''
#
#print(timeit.timeit(stmt=arcpy_stmt, setup=arcpy_setup, number=100))
