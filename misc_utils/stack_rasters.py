# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 09:43:27 2020

@author: disbr007
"""
import argparse
import os

from osgeo import gdal

from misc_utils.RasterWrapper import Raster, stack_rasters
from misc_utils.logging_utils import create_logger, create_module_loggers


logger = create_logger(__name__, 'sh', 'INFO')
# create_module_loggers('sh', 'info')

gdal.UseExceptions()


def main(args):
    rasters = args.rasters
    out_path = args.out_path
    
    logger.info('Stacking rasters...')
    stacked = stack_rasters(rasters)
    
    logger.info('Writing multiband raster...')
    ref = Raster(rasters[0])
    ref.WriteArray(stacked, out_path, stacked=True)
    
    ref = None
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-r', '--rasters', type=os.path.abspath, nargs='+',
                        help='Paths to the rasters to stack.')
    parser.add_argument('-o', '--out_path', type=os.path.abspath,
                        help='Path to write stacked, multiband raster to.')
    
    args = parser.parse_args()
    
    main(args)
