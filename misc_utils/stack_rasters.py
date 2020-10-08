# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 09:43:27 2020

@author: disbr007
"""
import argparse
import os

from osgeo import gdal
import numpy as np

from misc_utils.gdal_tools import stack_rasters
from misc_utils.raster_clip import clip_rasters
from misc_utils.logging_utils import create_logger, create_module_loggers

logger = create_logger(__name__, 'sh', 'INFO')

gdal.UseExceptions()


def main(args):
    rasters = args.input_rasters
    out_path = args.out_path
    # min_bb = args.min_bb
    rescale = args.rescale
    rescale_min = args.rescale_min
    rescale_max = args.rescale_max

    # if min_bb:
    #     logger.warning('Clipping to minimum bounding box not supported yet.')
        # rasters = clip_rasters()
    logger.info('Stacking rasters:\n{}'.format('\n'.join(rasters)))
    stacked = stack_rasters(rasters=rasters, out=out_path,
                            rescale=rescale,
                            rescale_min=rescale_min, rescale_max=rescale_max)

    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_rasters', type=os.path.abspath, nargs='+',
                        help='Paths to the rasters to stack.')
    parser.add_argument('-o', '--out_path', type=os.path.abspath,
                        help='Path to write stacked, multiband raster to.')
    # parser.add_argument('-mb', '--minbb', action='store_true',
    #                     help="""Use flag to clip to minimum bounding box of rasters.
    #                             Required for rasters of different dimensions.""")
    parser.add_argument('-r', '--rescale', action='store_true',
                        help='Use flag to rescale stacked rasters between 0 and 1.')
    parser.add_argument('--rescale_min', type=float,
                        help='If rescaling, minimum value to scale to.')
    parser.add_argument('--rescale_max', type=float,
                        help='If rescaling, maximum value to scale to.')

    args = parser.parse_args()
    
    main(args)
