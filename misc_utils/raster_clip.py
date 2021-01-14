# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:36:40 2019

@author: disbr007
Clip raster to shapefile extent. Must be in the same projection.
"""

import shutil

from osgeo import ogr, gdal
import os, logging, argparse

import geopandas as gpd
# import shapely

from misc_utils.gdal_tools import check_sr, ogr_reproject, get_raster_sr, \
    remove_shp
from misc_utils.id_parse_utils import read_ids
from misc_utils.logging_utils import create_logger


gdal.UseExceptions()
ogr.UseExceptions()


logger = create_logger(__name__, 'sh', 'INFO')
# sublogger = create_logger('misc_utils.gdal_tools', 'sh', 'INFO')


def move_meta_files(raster_p, out_dir, raster_ext=None):
    """Move metadata files associted with raster, skipping files with
       raster_ext if specified"""
    src_dir = os.path.dirname(raster_p)
    raster_name = os.path.splitext(os.path.basename(raster_p))[0]
    other_files = os.listdir(src_dir)
    meta_files = [f for f in other_files if f.startswith(raster_name)]
    if raster_ext:
        meta_files = [f for f in meta_files if not f.endswith(raster_ext)]

    for src_f in meta_files:
        src = os.path.join(src_dir, src_f)
        shutil.copy(src, out_dir)


def clip_rasters(shp_p, rasters, out_path=None, out_dir=None, out_suffix='_clip',
                 out_prj_shp=None, raster_ext=None, move_meta=False, 
                 in_mem=False, skip_srs_check=False, overwrite=False):
    """
    Take a list of rasters and warps (clips) them to the shapefile feature
    bounding box.
    rasters : LIST or STR
        List of rasters to clip, or if STR, path to single raster.
    out_prj_shp : os.path.abspath
        Path to create the projected shapefile if necessary to match raster prj
    """
    # TODO: Fix permission error if out_prj_shp not supplied -- create in-mem
    #  OGR?
    # Use in memory directory if specified
    if out_dir is None:
        in_mem = True
    if in_mem:
        out_dir = r'/vsimem'

    # Check that spatial references match, if not reproject (assumes all rasters have same projection)
    # TODO: support different extension (slow to check all of them in the loop below)
    # Check if list of rasters provided or if single raster
    if isinstance(rasters, list):
        check_raster = rasters[0]
    else:
        check_raster = rasters
        rasters = [rasters]

    if not skip_srs_check:
        logger.debug('Checking spatial reference match:\n{}\n{}'.format(shp_p, check_raster))
        sr_match = check_sr(shp_p, check_raster)
        if not sr_match:
            logger.debug('Spatial references do not match. Reprojecting to AOI...')
            if not out_prj_shp:
                out_prj_shp = shp_p.replace('.shp', '_prj.shp')
            shp_p = ogr_reproject(shp_p,
                                  to_sr=get_raster_sr(check_raster),
                                  output_shp=out_prj_shp)

    shp = gpd.read_file(shp_p)
    if len(shp) > 1:
        logger.debug('Dissolving clipping shape with multiple features...')
        shp['dissolve'] = 1
        shp = shp.dissolve(by='dissolve')
        shp_p = r'/vsimem/clip_shp_dissolve.shp'
        shp.to_file(shp_p)

    # Do the 'warping' / clipping
    warped = []
    for raster_p in rasters:
        # TODO: Handle this with platform.sys and pathlib.Path objects
        raster_p = raster_p.replace(r'\\', os.sep)
        raster_p = raster_p.replace(r'/', os.sep)

        # Create out_path if not provided
        if not out_path:
            if not out_dir:
                logger.debug('NO OUT_DIR')
            # Create outpath
            raster_out_name = '{}{}.tif'.format(
                os.path.basename(raster_p).split('.')[0], out_suffix)
            raster_out_path = os.path.join(out_dir, raster_out_name)
        else:
            raster_out_path = out_path

        # Clip to shape
        logger.debug('Clipping:\n{}\n\t---> '
                     '{}'.format(os.path.basename(raster_p),
                                 raster_out_path))
        if os.path.exists(raster_out_path) and not overwrite:
            logger.warning('Outpath exists, skipping: '
                           '{}'.format(raster_out_path))
            pass
        else:
            raster_ds = gdal.Open(raster_p, gdal.GA_ReadOnly)
            x_res = raster_ds.GetGeoTransform()[1]
            y_res = raster_ds.GetGeoTransform()[5]
            warp_options = gdal.WarpOptions(cutlineDSName=shp_p,
                                            cropToCutline=True,
                                            targetAlignedPixels=True,
                                            xRes=x_res,
                                            yRes=y_res)
            gdal.Warp(raster_out_path, raster_ds, options=warp_options)
            # Close the raster
            raster_ds = None
            logger.debug('Clipped raster created at {}'.format(raster_out_path))
            # Add clipped raster path to list of clipped rasters to return
            warped.append(raster_out_path)
        # Move meta-data files if specified
        if move_meta:
            logger.debug('Moving metadata files to clip destination...')
            move_meta_files(raster_p, out_dir, raster_ext=raster_ext)

    # Remove projected shp
    if in_mem is True:
        remove_shp(out_prj_shp)

    # If only one raster provided, just return the single path as str
    if len(warped) == 1:
        warped = warped[0]

    return warped


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('shape_path', type=os.path.abspath, help='Shape to clip rasters to.')
    parser.add_argument('--rasters', nargs='*', type=os.path.abspath,
                        help='Rasters to clip. Either paths directly to, directory, or text file of paths.')
    parser.add_argument('-o', '--out_dir', type=os.path.abspath, help='Directory to write clipped rasters to.')
    parser.add_argument('--out_suffix', type=str, help='Suffix to add to clipped rasters.')
    parser.add_argument('--raster_ext', type=str, default='.tif', help='Ext of input rasters.')
    parser.add_argument('--move_meta', action='store_true',
                        help='Use this flag to move associated metadata files to clip destination.')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite output files.')
    parser.add_argument('--dryrun', action='store_true', help='Prints inputs without running.')

    args = parser.parse_args()

    shp_path = args.shape_path
    rasters = args.rasters
    out_dir = args.out_dir
    out_suffix = args.out_suffix
    raster_ext = args.raster_ext
    move_meta = args.move_meta
    overwrite = args.overwrite
    dryrun = args.dryrun

    # Check if list of rasters given or directory
    if os.path.isdir(args.rasters[0]):
        logger.debug('Directory of rasters provided: {}'.format(args.rasters[0]))
        if not raster_ext:
            logger.warning('Directory provided, but no extension to identify rasters. Provide raster_ext.')
        r_ps = os.listdir(rasters[0])
        # logger.info(r_ps)
        rasters = [os.path.join(rasters[0], r_p) for r_p in r_ps if r_p.endswith(raster_ext)]
        if len(rasters) == 0:
            logger.error('No rasters provided.')
            raise Exception
    elif rasters[0].endswith('.txt'):
        rasters = read_ids(rasters[0])
    # If list passed as args, no need to parse paths


    logger.info('Input shapefile:\n{}'.format(shp_path))
    logger.info('Input rasters:\n{}'.format('\n'.join(rasters)))
    logger.info('Output directory:\n{}'.format(out_dir))

    if not dryrun:
        clip_rasters(shp_path, rasters, out_dir=out_dir, out_suffix=out_suffix, raster_ext=raster_ext,
                     move_meta=move_meta, overwrite=overwrite)
