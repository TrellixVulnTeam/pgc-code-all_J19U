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


#### Logging setup
# create logger
logger = logging.getLogger('valid_data')
logger.setLevel(logging.DEBUG)
# create file handler
#fh = logging.FileHandler(log)
#fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
#logger.addHandler(fh)
logger.addHandler(ch)

#logger.debug('Log file created at: {}'.format(log))


def valid_data(gdal_ds, write_valid=False, out_path=None):
    """
    Takes a gdal datasource and determines the number of
    valid pixels in it. Optionally, writing out the valid
    data as a binary raster. Assumes only one band in the
    input gdal datasource.
    gdal_ds      :    osgeo.gdal.Dataset
    write_valid  :    True to write binary raster, must supply out_path
    out_path     :    Path to write binary raster
    """
    # Get raster band - assumes only 1
    rb = gdal_ds.GetRasterBand(1)
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
        
        dst_ds = driver.Create(out_path, ds.RasterXSize, ds.RasterYSize, 1, rb.DataType)
        dst_ds.SetGeoTransform(ds.GetGeoTransform())
        out_prj = osr.SpatialReference()
        out_prj.ImportFromWkt(ds.GetProjectionRef())
        dst_ds.SetProjection(out_prj.ExportToWkt())
        for i in range(depth):
            b = i+1
            dst_ds.GetRasterBand(b).WriteArray(mask)
            dst_ds.GetRasterBand(b).SetNoDataValue(no_data_val)
        dst_ds = None

    return valid_pixels, total_pixels


def rasterize_shp2raster_extent(ogr_ds, gdal_ds, write_rasterized=False, out_path=None):
    """
    Rasterize a ogr datasource to the extent, projection, resolution, etc of a given
    gdal datasource object. Optionally write out the rasterized product.
    ogr_ds           :    osgeo.ogr.DataSource
    gdal_ds          :    osgeo.gdal.Dataset
    write_rasterised :    True to write rasterized product, must provide out_path
    out_path         :    Path to write rasterized product
    """
    # TODO: Add ability to provide field in ogr_ds to use to burn into raster.
    ## Get DEM attributes
#    dem_ds = gdal.Open(clip_dem)
    dem_no_data_val = gdal_ds.GetRasterBand(1).GetNoDataValue()
    dem_sr = gdal_ds.GetProjection()
    dem_gt = gdal_ds.GetGeoTransform()
    x_min = dem_gt[0]
    y_max = dem_gt[3]
    x_res = dem_gt[1]
    y_res = dem_gt[5]
    x_sz = ds.RasterXSize
    y_sz = ds.RasterYSize
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
    
    out_ds = driver.Create(mem_p, x_sz, y_sz, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform((x_min, x_res, 0, y_min, 0, -y_res))
    out_ds.SetProjection(dem_sr)
#    band = out_ds.GetRasterBand(1)
#    band.SetNoDataValue(dem_no_data_val) # fix to get no_data_val before(?) clipping rasters
#    band.FlushCache()
    
    gdal.RasterizeLayer(out_ds, [1], ogr_lyr, burn_values=[1])    
    
    if write_rasterized is False:
        return out_ds
    else:
        out_ds = None


prj_dir = r'E:\disbr007\projects\boise_greenland_dems\testing' 
out_dir = os.path.join(prj_dir, 'clipped')

box_p = os.path.join(prj_dir, 'term_poly.shp')
shp_ds = ogr.Open(box_p)

dem_p = os.path.join(prj_dir, 'SETSM_W1W1_20140421_102001002E4EBC00_102001002F144200_seg4_2m_v3.0_dem.tif')

#trans = translate(box_p, [dem_p], out_dir=out_dir, out_suffix='poly_trans')
warped = warp_rasters(box_p, [dem_p], out_dir, out_suffix='poly_clip_crop2cutline')

out_path = os.path.join(prj_dir, 'dem_mask.tif')
# Get number of valid pixels in each ds
for name, ds in warped.items():
    valid_pixels, total_pixels = valid_data(ds, write_valid=True, out_path=out_path)
    mem_p = os.path.join(prj_dir, 'rasterized.tif')
    mem_ds = rasterize_shp2raster_extent(shp_ds, ds, write_rasterized=False, out_path=mem_p)
    
    mem_rb = mem_ds.GetRasterBand(1)
    mem_arr = mem_rb.ReadAsArray()
    mem_valid_count = len(mem_arr[mem_arr==1])
    
    mem_ds = None
    dem_ds = None
    
    dem_valid = valid_pixels / mem_valid_count
    print(dem_valid)
