# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 15:35:32 2020

@author: disbr007
"""


import argparse
import os

from archive_analysis_utils import grid_aoi
from misc_utils.logging_utils import create_logger


logger = create_logger(__file__, 'sh')


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('aoi', type=os.path.abspath,
                        help='Path to AOI to create grid of.')
    parser.add_argument('out_path', type=os.path.abspath,
                        help='Path to write grid to.')
    parser.add_argument('--step', type=int,
                        help='Number of rows and columns to create.')
    parser.add_argument('--x_space', type=float,
                        help='horizontal spacing in units of AOI projection.')
    parser.add_argument('--y_space', type=float,
                        help='vertical spacing in units of AOI projection.')
    
    args = parser.parse_args()
    
    aoi = args.aoi
    out_path = args.out_path
    step = args.step
    x_space = args.x_space
    y_space = args.y_space
    
    grid = grid_aoi(aoi, step=step, x_space=x_space, y_space=y_space)
    
    logger.info('Grid size: {}'.format(len(grid)))
    logger.info('Writing grid to file...')
    
    grid.to_file(out_path)