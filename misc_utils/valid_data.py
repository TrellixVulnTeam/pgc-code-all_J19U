# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 12:46:20 2019

@author: disbr007
"""

import os
import logging
import numpy as np

from osgeo import gdal, ogr, osr

from clip2shp_bounds import warp_rasters
from gdal_tools import auto_detect_ogr_driver
from logging_utils import create_logger


#### Logging setup
logger = create_logger('valid_data', 'sh', 'INFO')


def valid_data(gdal_ds, band_number=1, write_valid=False, out_path=None):
    """
    Takes a gdal datasource and determines the number of
    valid pixels in it. Optionally, writing out the valid
    data as a binary raster.
    gdal_ds      (osgeo.gdal.Dataset):    osgeo.gdal.Dataset
    write_valid  (boolean)           :    True to write binary raster, 
                                          must supply out_path
    out_path     (str)               :    Path to write binary raster

    Writes     (Optional) Valid data mask as raster

    Returns
    Tuple:  Count of valid pixels, count of total pixels
    """
    # Check if gdal_ds is a file or already opened datasource
    if isinstance(gdal_ds, gdal.Dataset):
        pass
    elif os.path.exists(gdal_ds):
        gdal_ds = gdal.Open(gdal_ds)
    else:
        logger.warning('{} is neither path to gdal datasource or open datasource')
    # Get raster band
    rb = gdal_ds.GetRasterBand(band_number)
    no_data_val = rb.GetNoDataValue()
    arr = rb.ReadAsArray()
    # Create mask showing only valid data as 1's
    mask = np.where(arr!=no_data_val, 1, 0)
    # Count number of valid
    valid_pixels = len(mask[mask==1])
    total_pixels = mask.size
    
    # Write mask if desired
    if write_valid is True:
        if len(mask.shape) == 2:
            rows, cols = mask.shape
            depth = 1
        else:
            rows, cols, depth = mask.shape
        driver = gdal.GetDriverByName('GTiff')
        
        dst_ds = driver.Create(out_path, gdal_ds.RasterXSize, gdal_ds.RasterYSize, 1, rb.DataType)
        dst_ds.SetGeoTransform(gdal_ds.GetGeoTransform())
        out_prj = osr.SpatialReference()
        out_prj.ImportFromWkt(gdal_ds.GetProjectionRef())
        dst_ds.SetProjection(out_prj.ExportToWkt())
        for i in range(depth):
            b = i+1
            dst_ds.GetRasterBand(b).WriteArray(mask)
            dst_ds.GetRasterBand(b).SetNoDataValue(no_data_val)
        dst_ds = None

    return valid_pixels, total_pixels


def rasterize_shp2raster_extent(ogr_ds, gdal_ds, write_rasterized=False, out_path=None):
    """
    Rasterize a ogr datasource to the extent, projection, resolution of a given
    gdal datasource object. Optionally write out the rasterized product.
    ogr_ds           :    osgeo.ogr.DataSource
    gdal_ds          :    osgeo.gdal.Dataset
    write_rasterised :    True to write rasterized product, must provide out_path
    out_path         :    Path to write rasterized product
    
    Writes
    Rasterized dataset to file.

    Returns
    osgeo.gdal.Dataset
    or
    None
    """
    # If datasources are not open, open them
    if isinstance(ogr_ds, ogr.DataSource):
        pass
    else:
        ogr_ds = ogr.Open(ogr_ds)
        
    if isinstance(gdal_ds, gdal.Dataset):
        pass
    else:
        gdal_ds = gdal.Open(gdal_ds)
    # TODO: Add ability to provide field in ogr_ds to use to burn into raster.
    ## Get DEM attributes
    dem_no_data_val = gdal_ds.GetRasterBand(1).GetNoDataValue()
    dem_sr = gdal_ds.GetProjection()
    dem_gt = gdal_ds.GetGeoTransform()
    x_min = dem_gt[0]
    y_max = dem_gt[3]
    x_res = dem_gt[1]
    y_res = dem_gt[5]
    x_sz = gdal_ds.RasterXSize
    y_sz = gdal_ds.RasterYSize
    x_max = x_min + x_res * x_sz
    y_min = y_max + y_res * y_sz
    
    ## Open shapefile
    ogr_lyr = ogr_ds.GetLayer()
    
    # Create new raster in memory
    if write_rasterized is False:
        out_path = r'/vsimem/rasterized.tif'
        if os.path.exists(out_path):
            os.remove(out_path)
    driver = gdal.GetDriverByName('GTiff')
    
    out_ds = driver.Create(out_path, x_sz, y_sz, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform((x_min, x_res, 0, y_min, 0, -y_res))
    out_ds.SetProjection(dem_sr)
    band = out_ds.GetRasterBand(1)
    band.SetNoDataValue(dem_no_data_val) # fix to get no_data_val before(?) clipping rasters
    band.FlushCache()
    
    gdal.RasterizeLayer(out_ds, [1], ogr_lyr, burn_values=[1])    
    
    if write_rasterized is False:
        return out_ds
    else:
        out_ds = None
        return out_path


def valid_data_aoi(aoi, raster):
    """
    Compute percentage of valid pixels given an AOI.
    """
    aoi_gdal_ds = rasterize_shp2raster_extent(aoi, raster, write_rasterized=True, out_path=r'E:\disbr007\UserServicesRequests\Projects\kbollen\temp\aoi_temp_prj.tif')
    aoi_valid_pixels, aoi_total_pixels = valid_data(aoi_gdal_ds)
    # Pixels outside bounding box of AOI
    boundary_pixels = aoi_total_pixels - aoi_valid_pixels
    
    valid_pixels, total_pixels = valid_data(raster)
    possible_valid_pixels = total_pixels - boundary_pixels
    valid_perc = valid_pixels / possible_valid_pixels
    
    aoi_gdal_ds = None
    raster = None
    
    return valid_perc


    
# tr = r'E:\disbr007\UserServicesRequests\Projects\kbollen\dems\WV02_20130423_103001002272C900_1030010021137100_seg1_2m_dem_clip1.tif'
# aoi = r'E:\disbr007\UserServicesRequests\Projects\kbollen\temp\aoi_temp_prj.shp'
# aoi_gdal_ds = rasterize_shp2raster_extent(aoi, tr, write_rasterized=True, out_path=r'E:\disbr007\UserServicesRequests\Projects\kbollen\temp\aoi_temp_prj.tif')
# aoi_valid_pixels, aoi_total_pixels = valid_data(aoi_gdal_ds)
# # Pixels outside bounding box of AOI
# boundary_pixels = aoi_total_pixels - aoi_valid_pixels

# valid_pixels, total_pixels = valid_data(tr)
# possible_valid_pixels = total_pixels - boundary_pixels
# valid_perc = valid_pixels / possible_valid_pixels

# print(valid_perc)