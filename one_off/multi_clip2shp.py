# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 16:55:38 2019

@author: disbr007
Clips imagery in subdirectories to corresponding AOIs. AOIs shapefile
must have a field that matches the subdirectory names.
"""

import os
import logging

import geopandas as gpd

from clip2shp_bounds import warp_rasters
from logging_utils import create_logger


# logger = logging.getLogger('multi_clip2shp')
# logger.setLevel(logging.DEBUG)
# # create console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# # create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# # add the handlers to the logger
# logger.addHandler(ch)



# Inputs
PRJ_DIR = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark'
RAW_DIR = os.path.join(PRJ_DIR, 'raw')
CLIP_DIR = os.path.join(PRJ_DIR, 'clipped')
AOIS = os.path.join(PRJ_DIR, 'BITE_buffers.shp')


# Create logger
logger = create_logger('multi_clip2shp',
                       handler_type='sh',
                       handler_level='DEBUG')

# Load AOI polygons
aoi_master = gpd.read_file(AOIS)


# List imagery subdirectories
subdirs = os.listdir(RAW_DIR)


# Loop over imagery subdirectories and clip to appropriate AOI
for sd in subdirs:
    logger.info('Working on subdirectory: {}'.format(sd))
    # Select only aoi matching the current subdirectory and write (deleted later)
    aoi = aoi_master[aoi_master['subfolder']==int(sd)]
    aoi_outpath = os.path.join(PRJ_DIR, 'prj_files', 'temp', 'aoi_{}.shp'.format(sd))
    if not os.path.exists(os.path.dirname(aoi_outpath)):
        os.makedirs(os.path.dirname(aoi_outpath))
    aoi.to_file(aoi_outpath)
    
    # Create out subdirectory for clipped imagery
    out_subdir = os.path.join(CLIP_DIR, '{}_clip'.format(sd))
    if not os.path.exists(out_subdir):
        os.makedirs(out_subdir)
    # Loop over each image in subdirectory and clip to AOI
    for root, dirs, files in os.walk(os.path.join(RAW_DIR, sd)):
        rasters = [os.path.join(root, f)
                   for f in files 
                   if f.endswith('.tif') or f.endswith('.ntf')]
    
    logger.debug('Number of rasters: {}'.format(len(rasters)))
    logger.debug('Using {} as clip boundary...'.format(os.path.basename(aoi_outpath)))
    # warp_rasters(aoi_outpath, rasters=rasters, out_dir=out_subdir)
        