# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 11:21:17 2019

@author: disbr007

"""

import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator

import os, calendar, datetime, sys, logging, collections

from query_danco import query_footprint
#from utm_area_calc import utm_area_calc

#def main():
def locate_region(x):
    '''
    Returns a region name based on latitude. Used with df.apply and centroid latitudes
    x: centroid latitude as float
    '''
    if x < -60.0:
        return 'Antarctica'
    elif x > 60.0:
        return 'Arctic'
    else:
        return 'Non Polar'
    
    
def y_fmt(y, pos):
    '''
    Formatter for y axis of plots. Returns the number with appropriate suffix
    y: value
    pos: *Not needed?
    '''
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
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler(r'E:\disbr007\scratch\logs\monthly_rates.log', mode='w+')
    fh.setLevel(logging.INFO)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)


## LOAD DATA ##
# Specify columns to load for intrack and xtrack
in_cols = ['catalogid', 'stereopair', 'acqdate', 'cloudcover', 'platform', 'sqkm_utm']
x_cols = ['catalogid1', 'catalogid2', 'acqdate1', 'perc_ovlp']

# Read footprints from Danco using only specified column
logging.info('Loading intrack stereo...')
intrack = query_footprint(layer='dg_imagery_index_stereo', 
                          where="""cloudcover <= 50""", 
                          columns=in_cols)

def det_cc_cat(x):
    if x <= 20:
        return 'cc20'
    elif x <= 50:
        return 'cc21-50'
    
intrack['cc_cat'] = intrack['cloudcover'].apply(lambda x: det_cc_cat(x))

#logging.info('Loading xtrack stereo...')
# Use this query_footprint and following utm_area_calc to reload xtrack from Danco, else use load
# from pickle to use saved xtrack layer
#xtrack = query_footprint(layer='dg_imagery_index_xtrack_cc20', 
#                         where="""acqdate1 < '2019-06-01'""", 
#                         columns=x_cols)

## Add area column to xtrack (intrack already has one)
#logging.info('Adding area column to xtrack...')
#xtrack = utm_area_calc(xtrack)

# Saved pickle with utm areas calculated already
xtrack = pd.read_pickle(r'E:\disbr007\pgc_index\dg_imagery_index_xtrackcc20_2019jun10_utm.pkl')
#xtrack.to_pickle(r'E:\disbr007\pgc_index\dg_imagery_index_xtrackcc20_2019jun10_utm.pkl')
xtrack['cc_cat'] = 'cc20'

# Rename xtrack columns to align with intrack names
xtrack.rename(columns={
        'catalogid1': 'catalogid',
        'catalogid2': 'stereopair',
        'acqdate1': 'acqdate'},
        inplace=True)


## AGGREGATION BY MONTH AND REGION ##
# Put dfs into dictionary to loop over
in_name = 'Intrack'
x_name = 'Xtrack'
dfs = {}
dfs[in_name] = intrack
dfs[x_name] = xtrack

# Create dict to store only dataframes to plot (aggregated by month)
dfs2plot = {}

for name, stereo_type in dfs.items():
    logging.info('Aggregating {}...'.format(name))
    df = stereo_type
    
    ## Add region by centroid y (latitude)
    df['cent_y'] = df.centroid.y
    df['region'] = df['cent_y'].apply(lambda x: locate_region(x))

    # Convert date columns to datetime
    df['acqdate'] = pd.to_datetime(df['acqdate'])
    df.set_index('acqdate', inplace=True)
    
    # Aggregrate
    agg = {
           'catalogid': 'count',
           'sqkm_utm': 'sum'
           }
    dfs2plot[name] = df.groupby([pd.Grouper(freq='M'),'region', 'cc_cat']).agg(agg)
    dfs2plot[name].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
    
    # Create dfs for xtrack with area in given range
    if name == x_name:
        for n in ((250, 500), (500, 1000), (1000, np.inf)):
            dfs2plot['Xtrack {}'.format(n[0])] = df[(df['sqkm_utm'] >= n[0]) & (df['sqkm_utm'] < n[1])].groupby([pd.Grouper(freq='M'), 'region']).agg(agg)
            dfs2plot['Xtrack {}'.format(n[0])].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
#        dfs2plot['xtrack_500'] = df[df['sqkm_utm'] > 500 % df['sqkm_utm'] < 1000].groupby([pd.Grouper(freq='M')]).agg(agg)
#        dfs2plot['xtrack_500'].rename(columns={'catalogid': 'Pairs', 'sqkm_utm': 'Area'}, inplace=True)
 
# Create combined df of intrack and xtrack > 1k km^2
dfs2plot['Intrack + Xtrack 1k'] = dfs2plot[in_name].add(dfs2plot['Xtrack 1000'], fill_value=0)

# Add Node Hours column to each df
km_per_hour = 16.0
for name, df in dfs2plot.items():
    df['Node Hours'] = df['Area'] / km_per_hour


## Reset index for plotting (testing)
#for name, df in dfs2plot.items():
#    df.reset_index(level='region', inplace=True)


# Create ordered dictionary by key, to plot in correct order
dfs2plot = collections.OrderedDict(sorted(dfs2plot.items(), key=lambda kv: kv[0]))


## PLOTTING ##
#mpl.style.use('seaborn-darkgrid')
mpl.style.use('ggplot')
mpl.rcParams['axes.titlesize'] = 10

## Create plot and axes
nrows = 3
ncols = 6
fig, axes = plt.subplots(nrows=nrows, ncols=ncols, sharex='col', sharey='row', )

row_ct = 0
col_ct = 0


cols = ['Pairs', 'Area', 'Node Hours']
#cols = cols[::-1]
for col in cols:
#    print(col)
    for name, df in dfs2plot.items():
        ax = axes[row_ct][col_ct]
        df.unstack().plot.area(y=col, ax=ax, grid=True, legend=False, alpha=0.5) #color='black'
        if row_ct == 0:
            ax.set(title=name)
        if col == 'Node Hours':
            ax.set(ylabel='{} \n(${} km^2$ per hour)'.format(col, int(km_per_hour)), xlabel='')
        else:
            ax.set(ylabel=col, xlabel='')
        
        # Calculate min and max for column, grouping regions together by acqdate
        col_max = max([df[col].groupby('acqdate').sum().max() for name, df in dfs2plot.items()])
        col_min = min([df[col].groupby('acqdate').sum().min() for name, df in dfs2plot.items()])
        col_step = (col_max - col_min) / 10
        ax.set_ylim(col_min, col_max+col_step)

        # Format x and y axis
        formatter = FuncFormatter(y_fmt)
        ax.yaxis.set_major_formatter(formatter)
        ax.set_xlim('2007-01-01', '2019-06-01')
        plt.setp(ax.xaxis.get_majorticklabels(), 'rotation', 90)
        
        df.to_pickle(r'E:\disbr007\imagery_archive_analysis\imagery_rates\2019aug25\pickles\{}.pkl'.format(name))
            
        col_ct += 1
    col_ct = 0
    row_ct +=1

# Get legend info from last ax, use for a single figure legend    
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=3)
fig.suptitle('Stereo Archive Monthly Rates', size=14)
#plt.gcf().text(0.01, 0.02, '*Monthly stereo rates', 
#       ha='left', 
#       va='center', 
#       fontstyle='italic', 
#       fontsize='small')
plt.savefig(r'E:\disbr007\imagery_archive_analysis\imagery_rates\2019aug25\monthly_stereo_rates_region.jpg')

#if __name__ == '__main__':
#    main()

