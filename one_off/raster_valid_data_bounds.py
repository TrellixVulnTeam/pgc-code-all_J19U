# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 12:20:40 2019

@author: disbr007
"""

'''
Get boundaries of valid data from raster
'''

from osgeo import gdal
import numpy as np
import os

gdal.UseExceptions()


dem_p = r'V:\pgc\data\scratch\jeff\brash_island\dem\setsm\winter\brash_winter_dem_103001005BBD0900.tif'

def write_array(dem_p, arr2):
    data = gdal.Open(dem_p)
    arr = data.ReadAsArray()
    cols, rows = arr.shape
    trans = data.GetGeoTransform()
    proj = data.GetProjection()
    nodata_val = data.GetRasterBand(1).GetNoDataValue()
    
    outdriver = gdal.GetDriverByName('GTIFF')
    out_file = r'{}_test.tif'.format(dem_p.split('.tif')[0])
    outdata = outdriver.Create(str(out_file), rows, cols, 1, gdal.GDT_Float32)
    outdata.GetRasterBand(1).WriteArray(arr2)
    outdata.GetRasterBand(1).SetNoDataValue(nodata_val)
    outdata.SetGeoTransform(trans)
    outdata.SetProjection(proj)
    del outdata
