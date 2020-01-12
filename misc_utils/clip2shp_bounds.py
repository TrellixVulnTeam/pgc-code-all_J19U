# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:36:40 2019

@author: disbr007
Clip raster to shapefile extent. Must be in the same projection.
"""

from osgeo import ogr, gdal
import os, logging, argparse

from gdal_tools import check_sr, ogr_reproject, get_raster_sr
from logging_utils import create_logger


gdal.UseExceptions()
ogr.UseExceptions()


logger = create_logger('clip2shp_bounds', 'sh')


def warp_rasters(shp_p, rasters, out_dir=None, out_suffix='_clip',
                 out_prj_shp=None):
    """
    Take a list of rasters and warps (clips) them to the shapefile feature
    bounding box.
    out_prj_shp : os.path.abspath
        Path to create the projected shapefile if necessary to match raster prj.
    """
    # TODO: Add in memory ability: /vsimem/clipped.tif
    # Check that spatial references match, if not reproject (assumes all rasters have same projection)
    check_raster = rasters[0]
    logger.debug('Checking spatial reference match:\n{}\n{}'.format(shp_p, check_raster))
    sr_match = check_sr(shp_p, check_raster)
    if sr_match == False:
        logger.debug('Spatial references do not match.')
        shp_p = ogr_reproject(shp_p, to_sr=get_raster_sr(check_raster),
                              output_shp=out_prj_shp)

    # Do the 'warping' / clipping
    warped = {}
    for raster_p in rasters:
        raster_p = raster_p.replace(r'\\', os.sep)
        raster_p = raster_p.replace(r'/', os.sep)
        
        if not out_dir:
            out_dir == os.path.dirname(raster_p)

        
        # Clip to shape
        logger.info('Clipping {}...'.format(os.path.basename(raster_p)))
        raster_out_name = '{}{}.tif'.format(os.path.basename(raster_p).split('.')[0], out_suffix)
        raster_op = os.path.join(out_dir, raster_out_name)

        raster_ds = gdal.Open(raster_p)
        warp_options = gdal.WarpOptions(cutlineDSName=shp_p, cropToCutline=True)
        warped[raster_out_name] = gdal.Warp(raster_op, raster_ds, options=warp_options)
        logger.debug('Clipped raster created at {}'.format(raster_op))
            
    return warped
    

if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	parser.add_argument('shape_path', type=str, help='Shape to clip rasters to.')
	parser.add_argument('rasters', nargs='*', help='Rasters to clip.')
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
