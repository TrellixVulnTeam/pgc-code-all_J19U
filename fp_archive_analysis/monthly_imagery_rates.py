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
from matplotlib.ticker import FuncFormatter 

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
                       return '{val:d} {suffix}'.format(val=int(round(val)), suffix=suffix[i]) 
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
        'acqdate1': 'acqdate'}, inplace=True)


## Put dfs into dictionary to loop over
dfs = {}
dfs['Intrack'] = {'source': intrack}
dfs['Xtrack'] = {'source': xtrack}


for name, stereo_type in dfs.items():
    logging.info(name)
    df = stereo_type['source']
    
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
    dfs[name]['agg'].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)


## Plot aggregated columns
matplotlib.style.use('seaborn-darkgrid')

## Plotting params
date_range = ('2007-01-01', '2019-06-11')
xticks = range(2007, 2020, 2)
xlabel = 'Collection Date (Aggregated by Month)'

## Create plot and axes
fig, all_axes = plt.subplots(nrows=2, ncols=2)
axes = all_axes.ravel()
fig.suptitle('Stereo Archive')
ax_ct = -1 # Ax counter

for name, stereo_type in dfs.items():
    # Increase ax counter to move to next subplot
    ax_ct += 1
    
    # Unstack index
    df = dfs[name]['agg'].unstack()
    
    ## Area plot
    df.plot.area(y=[('Area', 'Arctic'), ('Area', 'Non Polar'), ('Area', 'Antarctica')],
                    ax=axes[ax_ct],
                    title='Area',
                    grid=True,
                    xlim=date_range,
                    xticks=xticks
                    )
    axes[ax_ct].set(xlabel=xlabel, ylabel='Area (sq. km)')
    
    ## IDs plot
    ax_ct += 1
    df.plot.area(y=[('Pairs', 'Arctic'), ('Pairs', 'Non Polar'), ('Pairs', 'Antarctica')],
                    ax=[ax_ct],
                    title='Pairs',
                    grid=True,
                    xlim=date_range,
                    xticks=xticks
                    )
    axes[ax_ct].set(xlabel=xlabel, ylabel='Pairs')

    # Format common ax operations
    # Mdates
    years = mdates.YearLocator()
    months = mdates.MonthLocator()
    yearsFmt = mdates.DateFormatter('%Y')
    
    for a in axes:
        # Set up date ticks
#        a.xaxis.set_major_locator(years)
#        a.xaxis.set_major_formatter(yearsFmt)
#        a.xaxis.set_minor_locator(months)
        a.xaxis.set_major_locator(plt.MaxNLocator(8))
        a.yaxis.set_major_locator(plt.MaxNLocator(10))
        a.format_xdata = mdates.DateFormatter('%Y')
        formatter = FuncFormatter(y_fmt)
        a.yaxis.set_major_formatter(formatter)
        # Legend Control
        handles, labels = a.get_legend_handles_labels()
        labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0], reverse=True))
        a.legend(handles, labels)

plt.tight_layout()
fig.autofmt_xdate()
fig.show()






