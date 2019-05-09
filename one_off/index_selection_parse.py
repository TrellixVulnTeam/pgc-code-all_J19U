# -*- coding: utf-8 -*-
"""
Created on Mon May  6 16:06:01 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import sys, os

sys.path.insert(0, r'C:\code\misc_utils')
from dataframe_utils import create_month_col, create_year_col

def percentage_col(df, col):
    '''
    add a column with percentages of the total that the given column represents
    (must be int or float col)
    '''
    
    total = df[col].sum()
    df['Percentage'] = df[col].apply(lambda x: 100 * (x/float(total)))

driver = 'ESRI Shapefile'

shp_path = r"E:\disbr007\UserServicesRequests\Projects\1536_GWU_kuklina\project_files\selected_imagery.shp"

shp = gpd.read_file(shp_path, driver=driver)

create_month_col(shp, 'ACQ_TIME')
create_year_col(shp, 'ACQ_TIME')

years = [2002, 2010, 2018]
months = [x for x in range(4,11)]
selection = shp[shp.Year.isin(years) & shp.Month.isin(months)]

selection['ACQ_TIME'] = selection['ACQ_TIME'].apply(lambda x: x.strftime('%Y-%m-%d'))
total_size = selection['FILE_SZ'].sum()

agg = {
       'SCENE_ID': {
               'num_scenes': 'count'
               },
       'ACQ_TIME': {
               'earliest_date': 'min',
               'latest_date': 'max',
               },
       'FILE_SZ': {
               'total_size': 'sum',
               'avg_size': 'mean'
               }
       }
  
sensor_summary_stats = selection.groupby('SENSOR').agg(agg)
yearly_summary_stats = selection.groupby('Year').agg(agg)
monthly_summary_stats = selection.groupby('Month').agg(agg)
percentage_col(sensor_summary_stats, ('SCENE_ID', 'num_scenes'))

out_path = os.path.join(os.path.dirname(shp_path), '{}_selection.shp'.format(os.path.basename(shp_path).split('.')[0]))
selection.to_file(out_path, driver=driver)