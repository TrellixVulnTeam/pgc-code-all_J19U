# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Add a month and year field to a vector layer
"""

import argparse
import logging
import os

import geopandas as gpd
import pandas as pd

from dataframe_utils import create_year_col, create_month_col, create_day_col


shp_p = r'E:\disbr007\UserServicesRequests\Projects\llarocca\selected_scenes.shp'
date_col = 'acq_time'
#out_p = r''
#overwrite = False

def main(shp_p, date_col, out_p=None, overwrite=False):
    ## Set up logging
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
    logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                        level=logging.INFO)
    lso = logging.StreamHandler()
    lso.setLevel(logging.INFO)
    lso.setFormatter(formatter)
    logger.addHandler(lso)
    
    ## Load file
    shp = gpd.read_file(shp_p)
    
    ## Add columns
    #date_cols = ['acqdate', 'acq_time', 'ACQDATE', 'ACQ_TIME']
    create_year_col(shp, date_col)
    create_month_col(shp, date_col)
    create_day_col(shp, date_col)
    
    
    ## Write file
    if overwrite:
        shp.to_file(shp_p)
    else:
        if not out_p:
            logger.info('Please specify an out path or use --overwrite.')
        shp.to_file(out_p)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    required_named = parser.add_argument_group('Required arguments')
    required_named.add_argument('-i', '--input', 
                        type=str,
                        help='Input OGR feature layer.')
    
    parser.add_argument('-d', '--date_col', 
                        type=str, 
                        default='acq_time',
                        help='Name of column containing date.')
    parser.add_argument('-o', '--out_path',
                        type=str,
                        help='Path to write output to.')
    parser.add_argument('--overwrite',
                        action='store_true',
                        help='''Flag to add new columns to existing file, rather than
                        creating a new file.''')
    
    args = parser.parse_args()
    
    main(args.input, args.date_col, args.out_path, args.overwrite)
    