# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:36:40 2019

@author: disbr007
Clip raster to shapefile extent. Must be in the same projection.
"""

from osgeo import ogr, gdal
import os, logging, argparse

from misc_utils.gdal_tools import check_sr, ogr_reproject, get_raster_sr, remove_shp
from misc_utils.logging_utils import create_logger


gdal.UseExceptions()
ogr.UseExceptions()


logger = create_logger(os.path.basename(__file__), 'sh')


def warp_rasters(shp_p, rasters, out_dir=None, out_suffix='_clip',
                 out_prj_shp=None, in_mem=False):
    """
    Take a list of rasters and warps (clips) them to the shapefile feature
    bounding box.
    rasters : LIST or STR
        List of rasters to clip, or if STR, path to single raster.
    out_prj_shp : os.path.abspath
        Path to create the projected shapefile if necessary to match raster prj.
        ** CURRENTLY MUST PROVIDE THIS ARG **
    """
    # TODO: Fix permission error if out_prj_shp not supplied -- create in-mem OGR?
    # Use in memory directory if specified
    if out_dir is None:
        in_mem = True
    if in_mem == True:
        out_dir = r'/vsimem'
    
    # Check that spatial references match, if not reproject (assumes all rasters have same projection)
    # TODO: support different extension (slow to check all of them in the loop below)
    # Check if list of rasters provided or if single raster
    if isinstance(rasters, list):
        check_raster = rasters[0]
    else:
        check_raster = rasters
        rasters = [rasters]
    
    logger.debug('Checking spatial reference match:\n{}\n{}'.format(shp_p, check_raster))
    sr_match = check_sr(shp_p, check_raster)
    if sr_match == False:
        logger.debug('Spatial references do not match.')
        if not out_prj_shp:
            out_prj_shp = shp_p.replace('.shp', '_prj.shp')
        shp_p = ogr_reproject(shp_p, 
                              to_sr=get_raster_sr(check_raster),
                              output_shp=out_prj_shp)

    # Do the 'warping' / clipping
    warped = []
    for raster_p in rasters:
        raster_p = raster_p.replace(r'\\', os.sep)
        raster_p = raster_p.replace(r'/', os.sep)
        
        if not out_dir:
            out_dir == os.path.dirname(raster_p)

        # Clip to shape
        logger.debug('Clipping {}...'.format(os.path.basename(raster_p)))
        # Create outpath 
        raster_out_name = '{}{}.tif'.format(os.path.basename(raster_p).split('.')[0], out_suffix)
        raster_op = os.path.join(out_dir, raster_out_name)

        raster_ds = gdal.Open(raster_p)
        x_res = raster_ds.GetGeoTransform()[1]
        y_res = raster_ds.GetGeoTransform()[5]
        warp_options = gdal.WarpOptions(cutlineDSName=shp_p, cropToCutline=True, 
                                        targetAlignedPixels=True, xRes=x_res, yRes=y_res)
        gdal.Warp(raster_op, raster_ds, options=warp_options)
        # Close the raster
        raster_ds = None
        logger.debug('Clipped raster created at {}'.format(raster_op))
        # Add clipped raster path to list of clipped rasters to return
        warped.append(raster_op)
    
    # Remove projected shp
    if in_mem is True:
        remove_shp(out_prj_shp)
    
    return warped


if __name__ == '__main__':

     parser = argparse.ArgumentParser()

     parser.add_argument('shape_path', type=str, help='Shape to clip rasters to.')
     parser.add_argument('rasters', nargs='*', help='Rasters to clip. Either paths directly to, or directory.')
     parser.add_argument('out_dir', type=os.path.abspath, help='Directory to write clipped rasters to.')
     parser.add_argument('--out_suffix', type=str, default='clip', help='Suffix to add to clipped rasters.')
     parser.add_argument('--raster_ext', type=str, default='.tif', help='Ext of input rasters.')
     parser.add_argument('--dryrun', action='store_true', help='Prints inputs without running.')
     args = parser.parse_args()

     shp_path = args.shape_path
     rasters = args.rasters
     out_dir = args.out_dir
     out_suffix = args.out_suffix

     # Check if list of rasters given or directory
     if os.path.isdir(args.rasters[0]):
        r_ps = os.listdir(args.rasters[0])
        rasters = [os.path.join(args.rasters[0], r_p) for r_p in r_ps if r_p.endswith(args.raster_ext)]

     if args.dryrun:
        print('Input shapefile: {}'.format(shp_path))
        print('Input rasters:\n{}'.format('\n'.join(rasters)))
        print('Output directory:\n{}'.format(out_dir))

     else:
        warp_rasters(shp_path, rasters, out_dir, out_suffix)
