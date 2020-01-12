# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 10:36:17 2020

@author: disbr007
"""
import os
from osgeo import ogr
from gdal_tools import auto_detect_ogr_driver, ogr_reproject, get_raster_sr
import copy

input_shp = r'E:\disbr007\UserServicesRequests\Projects\kbollen\temp\t1.shp'
output_shp = r'E:\disbr007\UserServicesRequests\Projects\kbollen\temp\out.shp'
raster = r'E:\disbr007\UserServicesRequests\Projects\kbollen\dems\000\1\WV01_20160414_102001005008D000_10200100487C6300_seg1_2m_dem_clip1.tif'

driver = ogr.GetDriverByName('ESRI Shapefile')

in_ds = driver.Open(input_shp)
print('Opened as ogr.DataSource:\n{}'.format(input_shp))
in_lyr = in_ds.GetLayer()
print('Got layer.')
in_prj = in_lyr.GetSpatialRef()
print('Got spatial ref.')
print(in_prj)


r_sr = get_raster_sr(raster)

out_shp = ogr_reproject(input_shp, to_sr=r_sr,
                        output_shp=output_shp)

in_ds = None

out_ds = driver.Open(output_shp)
print('Opened out_shp successfully.')
out_ds = None