# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 11:37:18 2019

@author: disbr007
Gets the number of footprints over each feature in grid AOI shapefile. It returns 
"""

import argparse, os
import geopandas as gpd
import pandas as pd
from archive_analysis_utils import get_count_loop, get_count
from query_danco import query_footprint


def merge_gdf(gdfs):
    '''merges a list of gdfs'''
    gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
    return gdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('footprint', type=str,
                        help='Danco layer name to calculate density on.')
    parser.add_argument('grid', type=str,
                        help='''Shapefile of features to calculate density
                        over. Can be point or polygon.''')
    parser.add_argument('out_path', type=str,
                        help='Path to write output shapefile to.')
    args = parser.parse_args()
    
    grid_path = os.path.abspath(args.grid)
    out_path = os.path.abspath(args.out_path)
    
    footprint = query_footprint(args.footprint, columns=['catalogid'])
    
    driver = 'ESRI Shapefile'
    grid = gpd.read_file(grid_path, driver=driver)
    results = get_count_loop(get_count, grid, footprint)
    results = merge_gdf(results)
    results.to_file(out_path, driver=driver)
        
if __name__ == '__main__':
    main()
    
