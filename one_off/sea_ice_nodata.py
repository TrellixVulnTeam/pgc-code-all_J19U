# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 14:00:21 2019

@author: disbr007
Resamples values in rasters to a new no data value.
"""

import os
from osgeo import gdal, osr
import numpy as np


gdal.UseExceptions()


def resample_nodata(nd1, nd2, nd3, nd4, out_path):
    ## Read source and metadata
    ds = gdal.Open(f_p)
    gt = ds.GetGeoTransform()
    
    prj = osr.SpatialReference()
    prj.ImportFromWkt(ds.GetProjectionRef())
    
    x_sz = ds.RasterXSize
    y_sz = ds.RasterYSize
#    src_nodata = ds.GetRasterBand(1).GetNoDataValue()
    dtype = ds.GetRasterBand(1).DataType
#    dtype = gdal.GetDataTypeName(dtype)

    
    ## Read as array and convert no data to -9999
    ar = ds.ReadAsArray()
    ar = np.where((ar == nd1) | (ar == nd2) | (ar == nd3) | (ar == nd4), out_nodata, ar)

    
    ## Write
    # Create intermediate directories
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fmt = 'GTiff'
    driver = gdal.GetDriverByName(fmt)
    dst_dtype = signed_dtype_lut[dtype]['dst']
    dst_ds = driver.Create(out_path, x_sz, y_sz, 1, dst_dtype)
    dst_ds.GetRasterBand(1).WriteArray(ar)
    dst_ds.SetGeoTransform(gt)
    dst_ds.SetProjection(prj.ExportToWkt())
    dst_ds.GetRasterBand(1).SetNoDataValue(out_nodata)
    
    dst_ds = None


#sea_ice_p = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice'
sea_ice_p = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\north'
out_dir = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\resampled_nd'


## Concentration raster no data values
con_miss = 2550
con_land = 2540
con_coast = 2530
con_pol = 2510

## Extent raster no data values
ext_miss = 255
ext_land = 254
ext_coast = 253
ext_pol = 210

## Output no data values
out_nodata = -9999

## Look up table for GDAL data types - dst is the signed version of src if applicable
signed_dtype_lut = {
        0: {'src': 'Unknown', 'dst': 0},
        1: {'src': 'Byte', 'dst': 1},
        2: {'src': 'UInt16', 'dst': 3},
        3: {'src': 'Int16', 'dst': 3},
        4: {'src': 'UInt32', 'dst': 5},
        5: {'src': 'Int32', 'dst': 5},
        6: {'src': 'Float32', 'dst': 6},
        7: {'src': 'Float64', 'dst': 7},
        8: {'src': 'CInt16', 'dst': 8},
        9:{'src': 'CInt32', 'dst': 9},
        10:{'src': 'CFloat32', 'dst': 10},
        11:{'src': 'CFloat64', 'dst': 11},
        }

ctr = 0
for root, dirs, files in os.walk(sea_ice_p):
    for file in files:
        f_p = os.path.join(root, file)
        out_path = os.path.join(out_dir, os.path.relpath(os.path.join(root, file), sea_ice_p))
        # Resample concentration rasters
        if file.endswith('_concentration_v3.0.tif'):
            resample_nodata(con_miss, con_land, con_coast, con_pol, out_path=out_path)
        # Resample extent rasters
        if file.endswith('_extent_v3.0.tif'):
            resample_nodata(ext_miss, ext_land, ext_coast, ext_pol, out_path=out_path)
        ctr += 1
        print(ctr)
