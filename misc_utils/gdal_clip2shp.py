# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 13:10:20 2019

@author: disbr007
"""

from osgeo import ogr, gdal, osr
import os, logging, argparse

from gdal_tools import ogr_reproject, get_shp_sr, get_raster_sr


gdal.UseExceptions()
ogr.UseExceptions()


# create logger with 'spam_application'
logger = logging.getLogger('gdal_clip2shp')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)

