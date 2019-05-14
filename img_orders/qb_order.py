# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 09:10:58 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import argparse, os, sys
import query_danco
from imagery_order_sheet_maker_module import create_sheets

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import date_words

  

def project_dir(out_path, out_name):
    # Directory to write shp and order to
    date_in_words = date_words(today=True)
    dir_name = r'PGC_order_{}_{}'.format(date_in_words, out_name)
    dir_path = os.path.join(out_path, dir_name)
    return dir_path, dir_name
    

def select_by_date(df, date_begin=1990, date_end=2100):
    selection = df[(df.acqdate > date_begin) & (df.acqdate < date_end)]
    return selection

def update_schema(df):
    schema = gpd.io.file.infer_schema(df)
    schema['properties']['acqdate'] = 'datetime'
    return schema

def write_selection(df, dir_path, dir_name):
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
#     Name of shapefile to write
    write_name = '{}.shp'.format(dir_name)
    # Location to write shapefile to
    shp_path = os.path.join(dir_path, write_name)
    ### Write the shapefile
    # Change datetime to appropriate type
    schema = update_schema(df)
    df.to_file(shp_path, driver='ESRI Shapefile', schema=schema)
    return shp_path

## Specify date of last refresh and refresh type
#out_path = r'E:\disbr007\imagery_orders'
#platform = 'QB02'
#end_date = '2004-01-01'
#begin_date = '1990-01-01'
##
##qb_noh = query_danco.query_footprint('dg_imagery_index_all_notonhand_cc20', where="platform = '{}'".format(platform))
##qb_noh['acqdate'] = pd.to_datetime(qb_noh.acqdate)
##qb_noh_2004 = qb_noh[qb_noh.acqdate < '2004']
##qb_noh.to_file
##
##prj_dir, prj_name = project_dir(output, refresh_type)
##selection = refresh(last_refresh=last_refresh, refresh_type='polar_hma_above')
##write_selection(selection, last_refresh=last_refresh, refresh_type=refresh_type, dir_path=prj_dir, dir_name=prj_name)
##create_sheets(selection, date2words(today=True), prj_dir)
#
#platform_noh = query_danco.query_footprint('dg_imagery_index_all_notonhand_cc20', where="platform = '{}'".format(platform))
#platform_noh['acqdate'] = pd.to_datetime(platform_noh.acqdate)
#selection = select_by_date(platform_noh, date_begin=begin_date, date_end=end_date)
#out_name = '{}_{}_to_{}'.format(platform, date2words(date=begin_date), date2words(date=end_date))
#dir_path = project_dir(out_path, out_name)
#shp_name = '{}.shp'.format(out_name)
#shp = write_selection(selection, dir_path, shp_name)


if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('begin_date', type=str, help='Earliest date to select. ("yyyy-mm-dd")')
    parser.add_argument('end_date', type=str, help='Latest date to select. ("yyyy-mm-dd")')
    parser.add_argument('platform', type=str, help='Platform to select')
    parser.add_argument('out_path', type=str, help='Where to right sheets.')
    args = parser.parse_args()
    begin_date = args.begin_date
    end_date = args.end_date
    platform = args.platform
    out_path = args.out_path
    
    # Do it
    platform_noh = query_danco.query_footprint('dg_imagery_index_all_notonhand_cc20', where="platform = '{}'".format(platform))
    platform_noh['acqdate'] = pd.to_datetime(platform_noh.acqdate)
    selection = select_by_date(platform_noh, date_begin=begin_date, date_end=end_date)
    out_name = '{}_{}_to_{}'.format(platform, date_words(begin_date), date_words(end_date))
    dir_path, dirname = project_dir(out_path, out_name)
    shp_name = '{}'.format(out_name)
    shp = write_selection(selection, dir_path, shp_name)
    