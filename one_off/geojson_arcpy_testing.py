# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 10:50:12 2019

@author: disbr007
"""

import arcpy
import geopandas as gpd
import logging, sys

from osgeo import gdal

gdal.UseExceptions()

#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


logger.info('Loading')
c_p = r'E:\disbr007\general\Countries_WGS84\Countries_WGS84.shp'
c = gpd.read_file(c_p, driver='ESRI Shapefile')

logger.info('Writing JSON')
geojson_p = r'E:\disbr007\general\Countries_WGS84\Countries_WGS84.geojson'
c.to_file(geojson_p, driver='GeoJSON')

logger.info('Writing feature class')
feat_p = r'C:\temp\scratch.gdb\geojson_countries'
arcpy.env.overwriteOutput = True
arcpy.env.workspace = r'C:\temp\scratch.gdb'
arcpy.JSONToFeatures_conversion(geojson_p, feat_p)
