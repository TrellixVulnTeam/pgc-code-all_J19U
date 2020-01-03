# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:36:40 2019

@author: disbr007
Clip raster to shapefile extent. Must be in the same projection.
"""

from osgeo import ogr, gdal, osr
import os, logging, argparse

from gdal_tools import ogr_reproject, get_shp_sr, get_raster_sr


gdal.UseExceptions()
ogr.UseExceptions()


# create logger with 'spam_application'
logger = logging.getLogger('clip2shp_bounds')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def warp_rasters(shp_p, rasters, out_dir, out_suffix='clip'):
    """
    Take a list of rasters and warps (clips) them to the shapefile feature
    bounding box.
    """
    # TODO: Add in memory ability: /vsimem/clipped.tif
    warped = {}
    for raster_p in rasters:
        if not out_dir:
            out_dir == os.path.dirname(raster_p)
        # Check that spatial references match, if not reproject
        logger.debug('Checking spatial reference match:\n{}\n{}'.format(shp_p, raster_p))
        sr_match = check_sr(shp_p, raster_p)
        if sr_match == False:
            logger.debug('Spatial references do not match.')
            sr_match = check_sr(shp_p, raster_p, reproject=True)
        
        # Clip to shape
        logger.info('Clipping {}...'.format(os.path.basename(raster_p)))
        raster_out_name = '{}_{}.tif'.format(os.path.basename(raster_p).split('.')[0], out_suffix)
        raster_op = os.path.join(out_dir, raster_out_name)

        raster_ds = gdal.Open(raster_p)
        warp_options = gdal.WarpOptions(cutlineDSName=shp_p, cropToCutline=True)
        warped[raster_out_name] = gdal.Warp(raster_op, raster_ds, options=warp_options)
        logger.debug('Clipped raster created at {}'.format(raster_op))
        
    return warped


def check_sr(shp_p, raster_p, reproject=False):
    """
    Check that spatial reference of shp and raster are the same.
    Optionally reproject in memory.
    """
     # Check for common spatial reference between shapefile and first raster
    shp_sr = get_shp_sr(shp_p)
    raster_sr = get_raster_sr(raster_p)
    
    if shp_sr != raster_sr:
        sr_match = False
    if sr_match == False and reproject == True:
        logger.info('''Spatial references do not match... 
                    Reprojecting shp to match raster...'''.format(shp_sr, raster_sr))
        shp_p = ogr_reproject(input_shp=shp_p, to_sr=raster_sr, in_mem=False)
        sr_match = True
    
    return sr_match
    

#def warp(shp_path, rasters, out_dir, out_suffix='clip'):
#    """
#    Wrapper function.
#    TODO: Write more.
#    """
#    # Check for common spatial reference between shapefile and first raster
#    shp_sr = get_shp_sr(shp_path)
#    raster_sr = get_raster_sr(rasters[0])
#    # Reproject if not same spatial reference
#    if shp_sr != raster_sr:
#        logger.info('''Spatial references do not match... 
#                    Reprojecting shp to match raster...'''.format(shp_sr, raster_sr))
#        shp_path = ogr_reproject(input_shp=shp_path, to_sr=raster_sr, in_mem=False)
##    
#    warped = warp_rasters(rasters, shp_path, out_dir=out_dir, out_suffix=out_suffix)
#    
#    return warped


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
