# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 09:43:27 2020

@author: disbr007
"""
import argparse
import os

from osgeo import gdal
import numpy as np

from misc_utils.RasterWrapper import Raster, stack_rasters
from misc_utils.logging_utils import create_logger, create_module_loggers


logger = create_logger(__name__, 'sh', 'INFO')
create_module_loggers('sh', 'info')

gdal.UseExceptions()


def main(args):
    rasters = args.input_rasters
    out_path = args.out_path
    minbb = args.minbb
    rescale = args.rescale

    logger.info('Stacking rasters:\n{}'.format('\n'.join(rasters)))
    stacked = stack_rasters(rasters, minbb=minbb, rescale=rescale,)

    if rescale:
        nodata_val = -9999
    else:
        nodata_val = None
    np.ma.set_fill_value(stacked, -9999)
    logger.info('Writing multiband raster...')
    ref = Raster(rasters[0])
    ref.WriteArray(stacked, out_path, stacked=True, dtype=gdal.GDT_Float64, nodata_val=nodata_val)
    
    ref = None
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_rasters', type=os.path.abspath, nargs='+',
                        help='Paths to the rasters to stack.')
    parser.add_argument('-o', '--out_path', type=os.path.abspath,
                        help='Path to write stacked, multiband raster to.')
    parser.add_argument('-mb', '--minbb', action='store_true',
                        help="""Use flag to clip to minimum bounding box of rasters.
                                Required for rasters of different dimensions.""")
    parser.add_argument('-r', '--rescale', action='store_true',
                        help='Use flag to rescale stacked rasters between 0 and 1.')

    args = parser.parse_args()
    
    main(args)
