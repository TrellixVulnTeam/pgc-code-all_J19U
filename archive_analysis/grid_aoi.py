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
logger = create_logger('archive_analysis_utils', 'sh', 'DEBUG')


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('aoi', type=os.path.abspath,
                        help='Path to AOI to create grid of.')
    parser.add_argument('out_path', type=os.path.abspath,
                        help='Path to write grid to.')
    parser.add_argument('--n_pts_x', type=int,
                        help='Number of rows to create.')
    parser.add_argument('--n_pts_y', type=int,
                        help='Number of columns to create.')
    parser.add_argument('--x_space', type=float,
                        help='horizontal spacing in units of AOI projection.')
    parser.add_argument('--y_space', type=float,
                        help='vertical spacing in units of AOI projection.')
    parser.add_argument('--poly', action='store_true',
                        help='Output the resulting grid as a polygon, rather '
                             'than the default points.')

    args = parser.parse_args()
    
    aoi = args.aoi
    out_path = args.out_path
    n_pts_x = args.n_pts_x
    n_pts_y = args.n_pts_y
    x_space = args.x_space
    y_space = args.y_space
    poly = args.poly

    logger.info('Creating grid...')
    grid = grid_aoi(aoi, n_pts_x=n_pts_x, n_pts_y=n_pts_y,
                    x_space=x_space, y_space=y_space,
                    poly=poly)
    
    logger.info('Grid size: {:,}'.format(len(grid)))
    logger.info('Writing grid to file: {}'.format(out_path))

    grid.to_file(out_path)
