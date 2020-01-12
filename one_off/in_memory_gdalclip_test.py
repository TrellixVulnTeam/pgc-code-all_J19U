# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 13:01:49 2020

@author: disbr007
"""

from osgeo import ogr, gdal

dem_p = r'E:\disbr007\UserServicesRequests\Projects\kbollen\dems\WV01_20160414_102001005008D000_10200100487C6300_seg1_2m_dem.tif'
dem_op = r'E:\disbr007\UserServicesRequests\Projects\kbollen\dems\WV01_20160414_102001005008D000_10200100487C6300_seg1_2m_dem_clip.tif'
shp_p = r'E:\disbr007\UserServicesRequests\Projects\kbollen\test.shp'


in_driver = ogr.GetDriverByName('ESRI Shapefile')
inds = in_driver.Open(shp_p)
inlyr = inds.GetLayer()

mem_driver = ogr.GetDriverByName('Memory')
mem_ds = mem_driver.CreateDataSource('mem')

temp = mem_driver.Open('mem', 1)

out = mem_ds.CopyLayer(inlyr, 'out', ['OVERWRITE=YES'])
mem_ds=None

warp_options = gdal.WarpOptions(cutlineDSName=out, cropToCutline=True)
gdal.Warp(dem_op, dem_p, options=warp_options)