# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 17:26:44 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import sys

from misc_utils.raster_clip import clip_rasters
from misc_utils.logging_utils import LOGGING_CONFIG


# Create logger
logging.config.dictConfig(LOGGING_CONFIG('DEBUG'))
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('aoi', type=os.path.abspath,
                        help="Path to AOI shapefile to clip to.")
    parser.add_argument('dems', type=os.path.abspath,
                        help="Path to text file of DEM paths.")
    parser.add_argument('out_dir', type=os.path.abspath,
                        help='Path to write clipped DEMs to.')
    parser.add_argument('--out_suffix', type=str, default='_clip',
                        help='Suffix to attach to clipped DEMs.')
    
    args = parser.parse_args()
    
    AOI_PATH = args.aoi
    dems_file = args.dems
    OUT_DIR = args.out_dir
    OUT_SUFFIX = args.out_suffix
    
    # Get DEM paths from text file
    DEMS = []
    with open(dems_file, 'r') as df:
        content = df.readlines()
        for dem_path in content:
            DEMS.append(dem_path.strip())
    
    # Check for existence of all DEMs
    does_not_exist = [dem for dem in DEMS if not os.path.exists(dem)]
    if len(does_not_exist) != 0:
        logger.error('Could not find DEM(s):\n{}'.format('\n'.join(does_not_exist)))
        sys.exit(-1)
        
    clip_rasters(AOI_PATH,
                 rasters=DEMS,
                 out_dir=OUT_DIR,
                 out_suffix=OUT_SUFFIX)


