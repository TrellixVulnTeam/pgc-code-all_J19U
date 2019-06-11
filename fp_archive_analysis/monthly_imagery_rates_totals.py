# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 11:21:17 2019

@author: disbr007

"""

import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator

import os, calendar, datetime, sys, logging, collections

from query_danco import query_footprint
from utm_area_calc import utm_area_calc


def locate_region(x):
    if x < -60.0:
        return 'Antarctica'
    elif x > 60.0:
        return 'Arctic'
    else:
        return 'Non Polar'
    
    
def y_fmt(y, pos):
    decades = [1e9, 1e6, 1e3, 1e0, 1e-3, 1e-6, 1e-9 ]
    suffix  = ["G", "M", "k", "" , "m" , "u", "n"  ]
    if y == 0:
        return str(0)
    for i, d in enumerate(decades):
        if np.abs(y) >=d:
            val = y/float(d)
            signf = len(str(val).split(".")[1])
            if signf == 0:
                return '{val:d} {suffix}'.format(val=int(val), suffix=suffix[i])
            else:
                if signf == 1:
                    if str(val).split(".")[1] == "0":
                       return '{val:d}{suffix}'.format(val=int(round(val)), suffix=suffix[i]) 
                tx = "{"+"val:.{signf}f".format(signf = signf) +"} {suffix}"
                return tx.format(val=val, suffix=suffix[i])
    return y
    
    
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
in_cols = ['catalogid', 'stereopair', 'acqdate', 'cloudcover', 'platform', 'sqkm_utm']
x_cols = ['catalogid1', 'catalogid2', 'acqdate1', 'perc_ovlp']

# Read footprints from Danco
logging.info('Loading intrack stereo...')
intrack = query_footprint(layer='dg_imagery_index_stereo_cc20', 
                          where="""acqdate < '2019-06-01'""", 
                          columns=in_cols)

logging.info('Loading xtrack stereo...')
#xtrack = query_footprint(layer='dg_imagery_index_xtrack_cc20', 
#                         where="""acqdate1 < '2019-06-01'""", 
#                         columns=x_cols)

## Add area column to xtrack (intrack already has one)
#logging.info('Adding area column to xtrack...')
#xtrack = utm_area_calc(xtrack)

# Saved pickle with utm areas calculated already
xtrack = pd.read_pickle(r'E:\disbr007\pgc_index\dg_imagery_index_xtrackcc20_2019jun10_utm.pkl')
#xtrack.to_pickle(r'E:\disbr007\pgc_index\dg_imagery_index_xtrackcc20_2019jun10_utm.pkl')


# Rename xtrack columns to align with intrack names
xtrack.rename(columns={
        'catalogid1': 'catalogid',
        'catalogid2': 'stereopair',
        'acqdate1': 'acqdate'},
        inplace=True)


## Put dfs into dictionary to loop over
in_name = 'Intrack'
x_name = 'Xtrack'
dfs = {}
dfs[in_name] = intrack
dfs[x_name] = xtrack

dfs2plot = {}

for name, stereo_type in dfs.items():
    logging.info('Aggregating {}...'.format(name))
    df = stereo_type
    
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
    dfs2plot[name] = df.groupby([pd.Grouper(freq='M')]).agg(agg)
    dfs2plot[name].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
    
    if name == x_name:
        for n in (250, 500, 1000):
            dfs2plot['Xtrack {}'.format(n)] = df[df['sqkm_utm'] >= n].groupby([pd.Grouper(freq='M')]).agg(agg)
            dfs2plot['Xtrack {}'.format(n)].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
#        dfs2plot['xtrack_500'] = df[df['sqkm_utm'] > 500 % df['sqkm_utm'] < 1000].groupby([pd.Grouper(freq='M')]).agg(agg)
#        dfs2plot['xtrack_500'].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
 

dfs2plot['Intrack + Xtrack 1k'] = dfs2plot[in_name].add(dfs2plot['Xtrack_1000'], fill_value=0)

# Add Node Hours
for name, df in dfs2plot.items():
    df['Node Hours'] = df['Area'] / 16.0

# Create ordered dictionary by key
dfs2plot = collections.OrderedDict(sorted(dfs2plot.items(), key=lambda kv: kv[0]))


## Plot aggregated columns
#matplotlib.style.use('seaborn-darkgrid')
matplotlib.style.use('ggplot')


## Create plot and axes
nrows = 3
ncols = 6
fig, axes = plt.subplots(nrows=nrows, ncols=ncols, sharex=True, sharey='row')

row_ct = 0
col_ct = 0


cols = ['Pairs', 'Area', 'Node Hours']
for col in cols:
    row_axes = []
    col_min = np.inf
    col_max = -np.inf
    for name, df in dfs2plot.items():
        ax = axes[row_ct][col_ct]
        row_axes.append(ax)
        df.plot.area(y=col, ax=ax, grid=True, legend=False, color='black', alpha=0.5)
        if row_ct == 0:
            ax.set(title=name)
        ax.set(ylabel=col, xlabel='')
        col_ct += 1
        
        if df[col].min() < col_min:
            col_min = df[col].min()
        if df[col].max() > col_max:
            col_max = df[col].max()
            
        for ax in row_axes:
            col_step = (col_max - col_min) / 10
            ax.set_ylim(col_min, col_max+col_step)
            formatter = FuncFormatter(y_fmt)
            ax.yaxis.set_major_formatter(formatter)
            ax.set_xlim('2007-01-01', '2019-06-01')
            plt.setp(ax.xaxis.get_majorticklabels(), 'rotation', 90)
            
    del row_axes

    col_ct = 0
    row_ct +=1
   

#fig.tight_layout()
#fig.suptitle('Stereo Archive')













