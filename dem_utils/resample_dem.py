# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 10:20:36 2019

@author: disbr007

"""

import argparse
import logging.config
import os

from osgeo import gdal, gdalconst

from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger, LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)


def resample_dem(src_dem, target_dem, dst_dem, resampleAlg='bilnear', cutline=None):
    """
    Resample a DEM to match another.
    """
    logger.info('Reading in source DEM...')
    src = gdal.Open(src_dem, gdalconst.GA_ReadOnly)
    src_prj = src.GetProjection()
    src_geotrans = src.GetGeoTransform()
    no_data = src.GetRasterBand(1).GetNoDataValue()

    logger.info('Loading DEM to match...')
    target = Raster(target_dem)
    x_res = target.pixel_width
    y_res = target.pixel_height
    if cutline:
        crop_to_cutline = True
    else:
        crop_to_cutline = False
    
    logger.info('Resampling source_dem to match target_dem...')
    warp_options = gdal.WarpOptions(xRes=x_res, yRes=y_res, resampleAlg=resampleAlg,
                                    srcNodata=no_data, dstNodata=no_data,
                                    targetAlignedPixels=True,
                                    cutlineDSName=cutline,
                                    cropToCutline=crop_to_cutline)

    gdal.Warp(dst_dem, src, options=warp_options)

    logger.info('Created DEM at: {}'.format(dst_dem))

    del src, target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('src_dem', type=os.path.abspath,
                        help='DEM to resample.')
    parser.add_argument('target_dem', type=os.path.abspath,
                        help='DEM to match')
    parser.add_argument('out_dem', type=os.path.abspath,
                        help='Path to create DEM at.')
    parser.add_argument('-ra', '--resampleAlg', default='bilinear',
                        help="""Resampling algorithm to use. Must be one of:
                                near, bilinear, cubic, cubicspline, lanczos,
                                average, mode, max, min, med, q1, q3""")
    parser.add_argument('--cutline', type=os.path.abspath,
                        help='Shapefile to crop to.')

    args = parser.parse_args()

    resample_dem(args.src_dem, args.target_dem, args.out_dem,
                 resampleAlg=args.resampleAlg,
                 cutline=args.cutline)