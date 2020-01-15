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
from tqdm import tqdm

from clip2shp_bounds import warp_rasters
from logging_utils import create_logger


# Create logger
logger = create_logger('multi_clip2shp',
                       handler_type='sh',
                       handler_level='INFO')


def multi_clip2shp(aoi_master, raster_parent_dir, subfolder_field,
                   clipped_dir=None, return_rasters=False,
                   dryrun=False):
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
    subdirs = [sd for sd in subdirs if os.path.isdir(os.path.join(raster_parent_dir, sd))]
    
    
    # Loop over imagery subdirectories and clip to appropriate AOI
    if return_rasters is True:
        # Create master dictionary of clipped raster paths and GDAL objects
        clipped = {}
    else:
        clipped = None
    # pbar = tqdm(subdirs)
    # for sd in pbar:
    for sd in subdirs:
        logger.info('Working on subdirectory: {}'.format(sd))
        # Select only aoi matching the current subdirectory and write (deleted later)
        aoi = aoi_master[aoi_master[subfolder_field]==int(sd)]
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
            for r in rasters:
                clipped_path = '{}_clip.tif'.format(r[:-4])
                if os.path.exists(clipped_path):
                    rasters.remove(r)
        
        logger.debug('Number of rasters: {}'.format(len(rasters)))
        logger.debug('Using {} as clip boundary...'.format(os.path.basename(aoi_outpath)))
        
        # Perform clipping for current subdirectory
        # pbar.set_description('Clipping {} rasters to {}'.format(len(rasters), os.path.basename(aoi_outpath)))
        if not dryrun:
            clipped_subdir_rasters = warp_rasters(aoi_outpath, rasters=rasters, out_dir=out_subdir,
                                                  out_prj_shp=os.path.join(os.path.dirname(aoi_outpath), 'prj.shp'))
        else:
            logger.info('Clipping to aoi: {}'.format(aoi_outpath))
            logger.info('Clipping {} rasters'.format(len(rasters)))
        # Add dictionary of clipped paths and GDAL datasources to master dict
        if return_rasters is True:
            clipped.extend(clipped_subdir_rasters)
    
    return clipped


aoi = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\BITE_buffers.shp'
r_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho_selected'
sf = 'subfolder'
cd = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho_clipped'


multi_clip2shp(aoi_master=aoi, raster_parent_dir=r_dir, subfolder_field=sf,
                clipped_dir=cd)

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser()
    
#     parser.add_argument('raster_directory', type=os.path.abspath,
#                         help='Path to directory holding subdirectories of rasters')
#     parser.add_argument('aoi_path', type=os.path.abspath,
#                         help='Path to AOI file with polygons to clip to.')
#     parser.add_argument('subfolder_field', type=str,
#                         help='''Name of field in AOI file that corresponds
#                                 to subdirectory names.''')
#     parser.add_argument('--clipped_dir', type=os.path.abspath,
#                         help='''Path to directory to create clipped rasters in 
#                                 subdirectories''')
#     parser.add_argument('--dryrun', action='store_true',
#                         help='Prints actions only.')
#     parser.add_argument('--debug', action='store_true',
#                         help='Set logging level to DEBUG')

#     args = parser.parse_args()
    
#     if args.debug is True:
#         logger.setLevel('DEBUG')
    
#     logger.info('Raster directory: {}'.format(args.raster_directory))
    
#     multi_clip2shp(args.aoi_path, args.raster_directory, args.subfolder_field,
#                    clipped_dir=args.clipped_dir,
#                    dryrun=args.dryrun)
    