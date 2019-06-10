# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 11:21:17 2019

@author: disbr007

"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os, calendar, datetime, sys, logging

from query_danco import query_footprint
from utm_area_calc import utm_area_calc


def locate_region(x):
    if x < -60.0:
        return 'Antarctica'
    elif x > 60.0:
        return 'Arctic'
    else:
        return 'Non Polar'
    
    
## Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(r'E:\disbr007\scratch\logs\monthly_rates.log', mode='w+')
    fh.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

## Load data
# Specify columns to load for intrack and xtrack
in_cols = ['catalogid', 'stereopair', 'acqdate', 'cloudcover', 'platform']
x_cols = ['catalogid1', 'catalogid2', 'acqdate1', 'perc_ovlp']

# Read footprints from Danco
logging.info('Loading intrack stereo...')
intrack = query_footprint(layer='dg_imagery_index_stereo_cc20', 
                          where="""acqdate < '2019-06-01'""", 
                          columns=in_cols)

logging.info('Loading xtrack stereo...')
xtrack = query_footprint(layer='dg_imagery_xtrack_cc20', 
                         where="""acqdate1 < '2019-06-01'""", 
                         columns=x_cols)

# Rename xtrack columns to align with intrack names
xtrack.rename(columns={
        'catalogid1': 'catalogid',
        'catalogid2': 'stereopair',
        'acqdate1': 'acqdate'})


## Add area column to xtrack (intrack already has one)
logging.info('Adding area column to xtrack...')
xtrack = utm_area_calc(xtrack)


## Put dfs into dictionary to loop over
dfs = {}
dfs['intrack'] = {'source': intrack}
dfs['xtrack'] = {'source': xtrack}


for name, df in dfs.items():
    ## Add region by centroid y (latitude)
    df['cent_y'] = df.centroid.y
    df['region'] = df['cent_y'].apply(lambda x: locate_region(x))
        
    ## Aggregate by month
    # Convert date columns to datetime
    df['acqdate'] = pd.to_datetime(df['acqdate'])
    df.set_index('acqdate', inplace=True)
    
    # Aggregrate
    agg = {
           'catalogid': 'count',
           'sqkm_utm': 'sum'      
           }
    dfs[name]['agg'] = df.groupby([pd.Grouper(freq='M'), 'region']).agg(agg)










