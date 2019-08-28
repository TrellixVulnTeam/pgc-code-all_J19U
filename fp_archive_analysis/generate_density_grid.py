# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 14:43:38 2019

@author: disbr007
"""

import argparse
import geopandas as gpd

from gpd_utils import grid_poly


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('input_grid', type=str, help='Grid to split.')
    parser.add_argument('nrows', type=int, help='Number of rows to subdivide input grid into.')
    parser.add_argument('ncols', type=int, help='Number of columns to subdivide input grid into.')
    parser.add_argument('out_grid', type=str, help='Path to write the new grid to.')
    
    args = parser.parse_args()
    
    input_grid = args.input_grid
    nrows = args.nrows
    ncols = args.ncols
    out_grid = args.out_grid
    
    src_grid = gpd.read_file(input_grid)
    new_grid = grid_poly(src_grid, nrows=nrows, ncols=ncols)
    new_grid.to_file(out_grid, driver='ESRI Shapefile')
