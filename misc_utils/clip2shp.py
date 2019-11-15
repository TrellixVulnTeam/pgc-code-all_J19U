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
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def get_shp_bounds(shp_path):
    """
    Get the bounds of a shapefile. Will return bounds of all features.
    TODO: Add params.
    """
    data_source = ogr.Open(shp_path, 0)
    layer = data_source.GetLayer()
    ulx, lrx, lry, uly = layer.GetExtent()
#   Ordered for gdal_translate
    projWin = [ulx, uly, lrx, lry]

    del layer
    del data_source

    logger.debug('Shapefile projWin: {}'.format(projWin))

    return projWin


def translate_rasters(rasters, projWin, out_dir, out_suffix='trans'):
    """
    Take a list of rasters and translates (clips) them to the projWin.
    """
    # Translate (clip) to minimum bounding box
    translated = {}
    for raster_p in rasters:
        if not out_dir:
            out_dir == os.path.dirname(raster_p)
        logger.info('Translating {}...'.format(raster_p))
        raster_out_name = '{}_{}.tif'.format(os.path.basename(raster_p).split('.')[0], out_suffix)
        raster_op = os.path.join(out_dir, raster_out_name)

        raster_ds = gdal.Open(raster_p)
        translated[raster_out_name] = gdal.Translate(raster_op, raster_ds, projWin=projWin)

    return translated


def translate(shp_path, rasters, out_dir, out_suffix='trans'):
    """
    Wrapper function.
    TODO: Write more.
    """
    # Check for common projection between shapefile and first raster
    shp_SR = get_shp_sr(shp_path)
    raster_SR = get_raster_sr(rasters[0])
#    print('shp epsg: {}'.format(shp_SR))
#    print('raster epsg: {}'.format(raster_SR))
    
    if shp_SR != raster_SR:
        logger.info('''Spatial references do not match... 
                    Reprojecting shp from \n{}\n to...\n {}'''.format(shp_SR, raster_SR))
        shp_path = ogr_reproject(input_shp=shp_path, to_sr=raster_SR, in_mem=False)
#    
    projWin = get_shp_bounds(shp_path)
    translate_rasters(rasters, projWin=projWin, out_dir=out_dir, out_suffix=out_suffix)


if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	parser.add_argument('shape_path', type=str, help='Shape to clip rasters to.')
	parser.add_argument('rasters', nargs='*', help='Rasters to clip.')
	parser.add_argument('out_dir', type=os.path.abspath, help='Directory to write clipped rasters to.')
	parser.add_argument('--out_suffix', type=str, default='trans', help='Suffix to add to clipped rasters.')
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
		translate(shp_path, rasters, out_dir, out_suffix)


# translate(r'E:\disbr007\umn\ms_proj_2019jul05\data\scratch\nuth_small_aoi.shp',
#           [r'V:\pgc\data\scratch\jeff\coreg\data\pairs\WV02_20120222-WV02_20160311\WV02_20120222_103001001109C500_1030010011108600_seg1_2m_matchtag.tif',
#            r'V:\pgc\data\scratch\jeff\coreg\data\pairs\WV02_20120222-WV02_20160311\WV02_20160311_1030010053625700_103001005350B300_seg1_2m_matchtag.tif'],
#           r'E:\disbr007\umn\ms_proj_2019jul05\data\scratch',
#           '_nuth')
