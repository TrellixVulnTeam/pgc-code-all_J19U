# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 16:55:38 2019

@author: disbr007
Clips imagery in subdirectories to corresponding AOIs. AOIs shapefile
must have a field that matches the subdirectory names.
"""

import argparse
import os

import geopandas as gpd

from clip2shp_bounds import warp_rasters
from logging_utils import create_logger


# Create logger
logger = create_logger('multi_clip2shp',
                       handler_type='sh',
                       handler_level='DEBUG')


def multi_clip2shp(aoi_master, raster_parent_dir, clipped_dir=None, return_rasters=False):
    """
    Take an aoi master OGR file with polygons for multiple AOIs and clips rasters in
    subdirectories in raster_parent_dir to the aoi corresponding to the subdirectory name.
    
    Parameters
    -------
    aoi_master : STR
        Path to AOI data source (any OGR supported format)
    raster_parent_dir : STR
        Path to parent directory holding subdirectories of rasters
    clipped_dir : STR
        Path to output clipped rasters (in subdirectories), existing or new
    return_rasters : BOOLEAN
        Set to True to return dictionary of clipped raster path and GDAL datasource
        (WARNING: MEMORY INTENSIVE)
        
    Returns
    -------
    LIST
        List of paths to newly clipped rasters
    """
    # Create clipped directory if it doesn't exists
    if clipped_dir is None:
        clipped_dir = os.path.join(os.path.dirname(raster_parent_dir), 'clipped')
        if not os.path.exists(clipped_dir):
            os.makedirs(clipped_dir)
    
    # Load AOI polygons
    aoi_master = gpd.read_file(aoi_master)
    
    
    # List imagery subdirectories
    subdirs = os.listdir(raster_parent_dir)
    
    
    # Loop over imagery subdirectories and clip to appropriate AOI
    if return_rasters is True:
        # Create master dictionary of clipped raster paths and GDAL objects
        clipped = {}
    for sd in subdirs:
        logger.info('Working on subdirectory: {}'.format(sd))
        # Select only aoi matching the current subdirectory and write (deleted later)
        aoi = aoi_master[aoi_master['subfolder']==int(sd)]
        aoi_outpath = os.path.join(os.path.dirname(raster_parent_dir), 'prj_files', 'temp', 'aoi_{}.shp'.format(sd))
        if not os.path.exists(os.path.dirname(aoi_outpath)):
            os.makedirs(os.path.dirname(aoi_outpath))
        aoi.to_file(aoi_outpath)
        
        # Create out subdirectory for clipped imagery
        out_subdir = os.path.join(clipped_dir, '{}_clip'.format(sd))
        if not os.path.exists(out_subdir):
            os.makedirs(out_subdir)
        # Loop over each image in subdirectory and clip to AOI
        for root, dirs, files in os.walk(os.path.join(raster_parent_dir, sd)):
            rasters = [os.path.join(root, f)
                       for f in files 
                       if f.endswith('.tif') or f.endswith('.ntf')]
        
        logger.debug('Number of rasters: {}'.format(len(rasters)))
        logger.debug('Using {} as clip boundary...'.format(os.path.basename(aoi_outpath)))
        
        # Perform clipping for current subdirectory
        clipped_subdir_rasters = warp_rasters(aoi_outpath, rasters=rasters, out_dir=out_subdir)
        
        # Add dictionary of clipped paths and GDAL datasources to master dict
        if return_rasters is True:
            clipped.extend(clipped_subdir_rasters)
            
    return clipped


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('raster_directory', type=os.path.abspath,
                        help='Path to directory holding subdirectories of rasters')
    parser.add_argument('aoi_path', type=os.path.abspath,
                        help='Path to AOI file with polygons to clip to.')

    args = parser.parse_args()
    
    multi_clip2shp(args.aoi_path, args.raster_parent_dir)
    