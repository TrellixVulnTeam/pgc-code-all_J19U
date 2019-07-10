# -*- coding: utf-8 -*-
"""
Created on Tue Jul  9 10:11:01 2019

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
from utm_area_calc import utm_area_calc


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


def plot_agg_timeseries(df, agg_col, agg_type, date_col, freq, ax=None):
    """
    df: dataframe to make histogram from
    agg_col: column to agg
    agg_type = type of aggregation on col -> 'count', 'sum', etc.
    date_col: column with date information, unaggregated
    freq: frequency of aggregation ('Y', 'M', 'D')
    ax: preexisting ax to plot on, defaults to creating a new one
    """
    ## Prep data
    # Convert date column to pandas datetime and set as index
    df[date_col] = pd.to_datetime(df[date_col])
    df.set_index(date_col, inplace=True)
    
    # Aggregate 
    agg = {agg_col: agg_type}
    agg_df = df.groupby([pd.Grouper(freq=freq)]).agg(agg)
    
    
    ## Plotting
    mpl.style.use('ggplot')
    if ax == None:
        fig, ax = plt.subplots(nrows=1, ncols=1)
    
    agg_df.plot.area(y=agg_col, ax=ax)
    
    formatter = FuncFormatter(y_fmt)
    ax.yaxis.set_major_formatter(formatter)
    plt.show()
    return fig, ax


def determine_season(date_col):
    """
    Takes a pd.datetime date column of a pandas dataframe and 
    returns the season
    """
    # Convert to datetime if not already
    if type(date_col) != pd._libs.tslibs.timestamps.Timestamp:
        date_col = pd.to_datetime(date_col)
#        print('converted to dtime')
    month = date_col.month
    year = date_col.year
    if month >= 7:
        season = '{}-{}'.format(str(year)[-2:], str(year+1)[-2:])
    elif month < 7:
        season = '{}-{}'.format(str(year-1)[-2:], str(year)[-2:])
    else:
        print('Month: {}'.format(month))
    return season


## Load and prep data
# Load intrack and xtrack
it = query_footprint('dg_imagery_index_stereo_cc20', where="y1 < -50", columns=['pairname', 'acqdate', 'sqkm_utm'])
it['type'] = 'intrack'

xt = query_footprint('dg_imagery_index_xtrack_cc20', 
                     where="project = 'REMA'", 
                     columns=['pairname', 'acqdate1', 'datediff'])
xt['type'] = 'cross-track'
xt = xt[xt['datediff'] <= 10]
# Calc area of xtrack
xt = utm_area_calc(xt)
# Rename xtrack columns to align with intrack names
xt.rename(columns={'acqdate1': 'acqdate'}, inplace=True)

# Load REMA pairnames as list
rema = list(query_footprint('esrifs_rema_strip_index', db='products', columns=['pairname'])['pairname'])

# Load regions
ant = query_footprint('pgc_world_aois', where="loc_name = 'Antarctica'", columns=['loc_name'])

## Do sjoin
it = gpd.sjoin(it, ant, how='inner')
xt = gpd.sjoin(xt, ant, how='inner')


## Combine intrack and xtrack
stereo = pd.concat([it, xt], ignore_index=True)

# Use REMA to determine released not released
stereo['released'] = np.where(stereo['pairname'].isin(rema), 'released', 'unreleased')


## Aggregation
# Parameters
agg_col = 'pairname'
agg_type = 'count'
date_col = 'acqdate'
freq = 'Y'

# Add a 'seeason' column: July 1-June 30
stereo[date_col] = pd.to_datetime(stereo[date_col])
stereo['season'] = stereo.apply(lambda x: determine_season(x['acqdate']), axis=1)
stereo = stereo[(stereo['acqdate'] >= '2009-07-01') & (stereo['acqdate'] <= '2019-06-30')]

agg = {agg_col: agg_type}
agg_df = stereo.groupby(['season', 'released', 'type']).agg(agg)


## Plotting
plt.style.use('ggplot')
fig, ax = plt.subplots(nrows=1, ncols=1)
bar_width = 0.4
agg_df.unstack(level='released')[('pairname', 'released')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, position=1, width=bar_width)
agg_df.unstack(level='released')[('pairname', 'unreleased')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, alpha=0.45, position=0, width=bar_width)

formatter = FuncFormatter(y_fmt)
ax.yaxis.set_major_formatter(formatter)
ax.set(ylabel='Number of Stereo DEMs', xlabel='Collection Season')
handles, labels = ax.get_legend_handles_labels()
labels = ['Released Cross-track', 'Released Intrack', 'Unreleased Cross-track', 'Unreleased Intrack']
fig.legend(handles, labels, ncol=1)
fig.suptitle('Antarctic Stereo DEMs', size=14)
plt.tight_layout()


# Combined intrack and crosstrack
agg_df2 = stereo.groupby(['season', 'released']).agg(agg)
fig2, ax2 = plt.subplots(nrows=1, ncols=1)
agg_df2.unstack(level='released')[('pairname', 'released')].plot(kind='bar', color='green', stacked=False, ax=ax2, legend=False, position=1, width=bar_width)
agg_df2.unstack(level='released')[('pairname', 'unreleased')].plot(kind='bar', color='green', stacked=False, ax=ax2, legend=False, alpha=0.45, position=0, width=bar_width)

ax2.yaxis.set_major_formatter(formatter)
ax2.set(ylabel='Number of Stereo DEMs', xlabel='Collection Season')
handles, labels = ax2.get_legend_handles_labels()
labels = ['Released', 'Unreleased']
fig2.legend(handles, labels, ncol=1)

fig2.suptitle('Antarctic Stereo DEMs', size=14)
plt.tight_layout()



