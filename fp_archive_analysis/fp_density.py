# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 11:37:18 2019

@author: disbr007
"""

import argparse, os
import geopandas as gpd
from archive_analysis_utils import get_density


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
    
    out_path = os.path.abspath(args.out_path)
    
    driver = 'ESRI Shapefile'
    grid = gpd.read_file(args.grid, driver=driver)
    
    get_density(args.footprint, grid, write_path=out_path)
    
    
if __name__ == '__main__':
    main()