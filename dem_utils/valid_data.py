# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 12:46:20 2019

@author: disbr007
"""

import os
import logging
import numpy as np

from osgeo import gdal, ogr, osr

from misc_utils.raster_clip import clip_rasters
from misc_utils.gdal_tools import auto_detect_ogr_driver, remove_shp
from misc_utils.logging_utils import create_logger


#### Logging setup
logger = create_logger('valid_data', 'sh', 'DEBUG')


def valid_data(gdal_ds, band_number=1, valid_value=None, write_valid=False, out_path=None):
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
    # TODO: Only check within acutal bounds of image, not edges
    # Check if gdal_ds is a file or already opened datasource
    if isinstance(gdal_ds, gdal.Dataset):
        pass
    # elif os.path.exists(gdal_ds):
        # gdal_ds = gdal.Open(gdal_ds)
    else:
        try:
            gdal_ds = gdal.Open(gdal_ds)
        except Exception as e:
            logger.error('Cannot open {}'.format(gdal_ds))
            logger.error(e)
            raise e
        # logger.warning('{} is neither path to GDAL datasource or open datasource'.format(gdal_ds))
    # Get raster band
    rb = gdal_ds.GetRasterBand(band_number)
    no_data_val = rb.GetNoDataValue()
    arr = rb.ReadAsArray()
    # Create mask showing only valid data as 1's
    if valid_value is not None:
        mask = np.where(arr == valid_value, 1, 0)
    else:
        mask = np.where(arr != no_data_val, 1, 0)
    # Count number of valid
    valid_pixels = len(mask[mask == 1])
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


def valid_percent(gdal_ds, band_number=1, valid_value=None, write_valid=False, out_path=None):
    valid, total = valid_data(gdal_ds=gdal_ds, band_number=band_number, valid_value=valid_value,
                              write_valid=write_valid, out_path=out_path)
    vp = valid / total
    vp = round(vp*100, 2)

    return vp


def rasterize_shp2raster_extent(ogr_ds, gdal_ds, write_rasterized=False, out_path=None):
    """
    Rasterize a ogr datasource to the extent, projection, resolution of a given
    gdal datasource object. Optionally write out the rasterized product.
    ogr_ds           :    osgeo.ogr.DataSource OR os.path.abspath
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
    logger.debug('Rasterizing OGR DataSource: {}'.format(ogr_ds))
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
    gdal_ds = None

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
    
    # if write_rasterized is False:
    #     return out_ds
    # else:
    #     out_ds = None
    #     return out_path
    out_ds = None
    return out_path


def valid_data_aoi(aoi, raster, out_dir=None, in_mem=True, write_rasterized=False):
    """
    Compute percentage of valid pixels given an AOI. The raster MUST ALREADY BE CLIPPED
    to the AOI to return valid results.
    
    out_dir : os.path.abspath
        Path to write rasterized AOI to.
    """
    logger.debug('Finding percent of {} valid pixels in {}'.format(raster, aoi))
    
    # Create in memory out_dir if needed
    if in_mem or not out_dir:
        out_dir = r'/vsimem'

    # Convert aoi to raster and count the number of pixels
    if isinstance(aoi, ogr.DataSource):
        out_path = os.path.join(out_dir, '{}.tif'.format(aoi.GetName()))
    else:
        out_path = os.path.join(out_dir, '{}.tif'.format(os.path.basename(aoi).split('.')[0]))
    
    aoi_gdal_ds = rasterize_shp2raster_extent(aoi, raster, write_rasterized=write_rasterized)
    aoi_valid_pixels, aoi_total_pixels = valid_data(aoi_gdal_ds)
    # Pixels outside bounding box of AOI
    boundary_pixels = aoi_total_pixels - aoi_valid_pixels
    
    # Get the number of valid pixels in the raster
    valid_pixels, total_pixels = valid_data(raster)
    # Get total number of pixels within the footprint
    possible_valid_pixels = total_pixels - boundary_pixels
    valid_perc = valid_pixels / possible_valid_pixels
    valid_perc = valid_perc*100
    valid_perc = round(valid_perc, 2)
    
    aoi_gdal_ds = None
    raster = None
    
    return valid_perc


def valid_percent_clip(aoi, raster, out_dir=None):
    """
    Clip a raster to the aoi, and get the percent of non-NoData pixels in the AOI.
    Useful with pandas.apply function applied to a row with a raster filename.

    Parameters
    ----------
    aoi : os.path.abspath
        Path to shapefile of AOI.
    raster : os.path.abspath
        Path to raster to check number of valid pixels.
    out_dir : os.path.abspath
        Path to place clipped DEMs if in-memory is not desired.
    threshold: INT
        Threshold above which to write out clipped raster.
    thresh_dir: STR
        Directory to write clipped rasters to. Will be written with original filename.

    Returns
    -------
    FLOAT : percentage of valid pixels

    """
    if out_dir is None:
        in_mem = True
        out_dir = r'/vsimem'
        
    clipped_path = clip_rasters(aoi, rasters=raster, in_mem=in_mem, out_dir=out_dir)[0]
    clipped_raster = gdal.Open(clipped_path)
    valid_perc = valid_data_aoi(aoi=aoi, raster=clipped_raster, out_dir=out_dir)
    valid_perc = round(valid_perc, 2)
    
    return valid_perc
