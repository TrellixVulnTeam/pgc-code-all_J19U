# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 08:46:36 2019

@author: disbr007
"""


import argparse
import geopandas as gpd
import logging
import sys

from archive_analysis_utils import get_count
from query_danco import list_danco_footprint, query_footprint


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('input_grid', type=str, help='Grid to count density on.')
    parser.add_argument('input_footprint', type=str, help='Footprint to calculate density of.')
    parser.add_argument('out_path', type=str, help='Path to write the density shapefile.')
    
    args = parser.parse_args()
    
    grid_p = args.input_grid
    footprint_p = args.input_footprint
    out_path = args.out_path
    
    try:
        logging.info('Loading grid...')
        grid = gpd.read_file(grid_p)
    except:
        logging.info('Input grid unsupported or not found. Must be shapefile. {}'.format(grid_p))
    
    danco_footprints = list_danco_footprint()
    if footprint_p in danco_footprints:
        logging.info('Loading footprint from danco...')
        footprint = query_footprint(footprint_p)
    else:
        try:
            logging.info('Loading footprint...')
            footprint = gpd.read_file(footprint_p, driver='ESRI Shapefile')
        except:
            logging.info('Input footprint unsupported or not found. Must be shapefile. {}'.format(footprint_p))
            sys.exit()
    
    logging.info('Calculating density...')
    density = get_count(grid, footprint)
    logging.info('Writing density...')
    density.to_file(out_path, driver='ESRI Shapefile')
    
    