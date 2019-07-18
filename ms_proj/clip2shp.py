# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 14:44:41 2019

@author: disbr007
Takes paths to DEMs, or a directory containing DEMs and applies gdal_translate
to clip to given shapefile's extent, rounded to the nearest whole coordinate.
"""

from osgeo import ogr, gdal
import os, logging


## Set up logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
gdal.UseExceptions()

## Directory containing dems and shp path
dems_dir = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\raw'
shp_path = r"V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\aoi_prj.shp"


## Load Shapefile to clip rasters and get extent
driver = ogr.GetDriverByName("ESRI Shapefile")
ds = driver.Open(shp_path, 0)
lyr = ds.GetLayer()
extent = list(lyr.GetExtent())
logging.info('Shapefile extent: {}'.format(extent))

# Round extent to nearest whole value, making extent bigger to cover full area
#extent = [ulx, lrx, lry, uly]
for i, x in enumerate(extent):
    if x < 0:
        extent[i] = int(x-1)
    else:
        extent[i] = int(x+1)


## Get all DEMs in directory
dems = []
for root, dirs, files in os.walk(dems_dir):
    for f in files:
        if f.endswith('_dem.tif'):
            dems.append(os.path.join(root, f))


## gdal_translate
for dem_p in dems:
    dem_dir = os.path.dirname(dem_p)
    dem_out_name = '{}_trans.tif'.format(os.path.basename(dem_p).split('.')[0])
    
    dem_ds = gdal.Open(dem_p)
    dem_op = os.path.join(dem_dir, dem_out_name)
    
    # Clip to shapefile extent
    logging.info('Translating {}...'.format(dem_p))
    gdal.Translate(dem_op, dem_ds, projWin= [extent[0], extent[3], extent[1], extent[2]]) #[ulx, uly, lrx, lry]
    
