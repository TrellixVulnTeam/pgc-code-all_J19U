# -*- coding: utf-8 -*-
"""
Created on Tue Jul  2 13:20:20 2019

@author: disbr007
"""


import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator
from functools import reduce

import os, calendar, datetime, sys, logging, collections, tqdm

from query_danco import query_footprint
from id_parse_utils import read_ids


def range_tuples(start, stop, step):
    
    ranges = []
    lr = range(start, stop+step, step)
    for i, r in enumerate(lr):
        if i < len(lr)-1:
            ranges.append((r, lr[i+1]))
    return ranges


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



#### LOAD DATA
# Dict to store dfs
dfs = {'DG_Archive': {},
       'DG_cc20': {},
       'DG_cc50': {},
       'Intrack_cc20': {},
       'Intrack_cc50': {},
       'Cross_Track': {},
       'Mono': {}}

ordered = ['DG_Archive', 'DG_cc20', 'DG_cc50', 'Intrack_cc20', 'Intrack_cc50', 'Cross_Track', 'Mono']
dfs = collections.OrderedDict((k, dfs[k]) for k in ordered)

data_path = r'E:\disbr007\imagery_archive_analysis\onhand_analysis\data'

##### Load pickles
for name, subdict in dfs.items():
    subdict['agg'] = pd.read_pickle(os.path.join(data_path, '{}_agg.pkl'.format(name)))
#    subdict['base'] = pd.read_pickle(os.path.join(data_path, '{}_base.pkl'.format(name)))
    subdict['totals'] = pd.read_pickle(os.path.join(data_path, '{}_totals.pkl'.format(name)))


#### PLOT TOTAL IDS AND PERCENTAGE OF WHOLE FOR EACH BREAKDOWN
mpl.style.use('ggplot')
mpl.rcParams['axes.titlesize'] = 10

## Create plot and axes
nrows = 2
dg_cols = 3
cat_cols = 4
dg_fig, dg_axes = plt.subplots(nrows=nrows, ncols=dg_cols, sharex='col', sharey='row', )
cat_fig, cat_axes = plt.subplots(nrows=nrows, ncols=cat_cols, sharex='col', sharey='row')
# Counters for ax array
row_ct = 0
dg_col_ct = 0
cat_col_ct = 0
cmap = ListedColormap([sns.xkcd_rgb["dull red"], sns.xkcd_rgb['medium green'], sns.xkcd_rgb['azul']])

#plots = ['Strips']
#for plot in plots:
dg_plots = ['DG_Archive', 'DG_cc20', 'DG_cc50']
for name, sub_dict in dfs.items():
    row_ct = 0
    if name in dg_plots:
        col_ct = dg_col_ct
        axes = dg_axes
#        ax = dg_axes[row_ct][dg_col_ct]
    else:
        col_ct = cat_col_ct
        axes = cat_axes
    
    ax = axes[row_ct][col_ct]
    if col_ct == 0:
        ax.set(ylabel='Percentage')
    else:
        ax.set(ylabel='', xlabel='')   
        
    tot_df = sub_dict['totals']
    agg_df = sub_dict['agg']
    
    ax.set(title=name.replace('_', ' '))
#        ax = axes[col_ct] # if only one row
    cols =[('Strips', 'PGC'), ('Strips', 'NASA'), ('Strips', 'Not Onhand')]
    tot_df = tot_df[cols]
    agg_df = agg_df[cols]

    tot_df.plot.area(ax=ax, grid=True, alpha=0.6, legend=False, linewidth=0.5, colormap=cmap) # color='black'
    ax.set_ylim(0, 100)
    row_ct +=1
    ax = axes[row_ct][col_ct]
    agg_df.plot.area(ax=ax, grid=True, alpha=0.6, legend=False, linewidth=0.5, colormap=cmap)

    
    # Calculate min and max for all dfs, use as lims
    if name in dg_plots:
        col_max = max([sd['agg'].max().max() for n, sd in dfs.items() if n in dg_plots])
        col_min = min([sd['agg'].min().min() for n, sd in dfs.items() if n in dg_plots])
        col_step = (col_max - col_min) / 10
    else:
        col_max = max([sd['agg'].max().max() for n, sd in dfs.items() if n not in dg_plots])
        col_min = min([sd['agg'].min().min() for n, sd in dfs.items() if n not in dg_plots])
        col_step = (col_max - col_min) / 10
    
    ax.set_ylim(col_min, col_max+col_step)
    
    if col_ct == 0:
        ax.set(ylabel='Total Strips')
    else:
        ax.set(ylabel='', xlabel='')        

    # Format x and y axis
    formatter = FuncFormatter(y_fmt)
    ax.yaxis.set_major_formatter(formatter)
    ax.set_xlim('2008-01-01', '2019-03-01')
    plt.setp(ax.xaxis.get_majorticklabels(), 'rotation', 90)
    ax.set(xlabel='')
    if name in dg_plots:
        dg_col_ct += 1
    else:
        cat_col_ct +=1
        

# Get legend info from last ax, use for a single figure legend    
handles, labels = dg_axes[0][0].get_legend_handles_labels()
labels = ['PGC', 'NASA', 'Not On Hand']
dg_fig.legend(handles, labels, loc='lower center', ncol=1)
handles, labels = cat_axes[0][0].get_legend_handles_labels()
labels = ['PGC', 'NASA', 'Not On Hand']
cat_fig.legend(handles, labels, loc='lower center', ncol=1)


#### Plot COLLECTION vs. RECEIVED AND EXTRAPOLATE FORWARD
## Load take per month (from Danny)
received = pd.read_csv(os.path.join(data_path, 'orders_received2019jul07.csv'),
                   parse_dates=[[0, 1]])
received.rename({'Number of orders received': 'received'}, axis='columns', inplace=True)
received.set_index('month_year', inplace=True)
rate = received['2019-01':'2019-06']['received'].mean()

# Get cumulative rates
df = dfs['DG_Archive']['agg']
oh = df[('Strips', 'NASA')].fillna(0).add(df[('Strips', 'PGC')]).fillna(0).to_frame()
oh['cumul'] = oh[0].cumsum()

# Extend On hand for 5 years at a rate of 48,000 IDs per month (6 month avg orders received)
ext_dates = pd.date_range('2019-05-01', periods=60, freq='M')
ext_vals = np.arange(oh['cumul'].max(), 4657841.0, rate)
ext = pd.DataFrame({'acqdate':ext_dates, 'Strips': ext_vals})
ext.set_index('acqdate', inplace=True)

# Entire DG Archive
collect = df[('Total', '')].to_frame()
collect['cumul'] = collect[('Total', '')].cumsum()
collect_rate = collect[('Total', '')]['2019-01':'2019-04'].mean()
coll_ext_vals = np.arange(collect['cumul'][:'2019-05'].max(), 10710638, collect_rate)
coll_ext = pd.DataFrame({'acqdate':ext_dates, 'Strips':coll_ext_vals})
coll_ext.set_index('acqdate', inplace=True)

# DG Archive cc20
collcc20 = dfs['DG_cc20']['agg'][('Total','')].to_frame()
collcc20['cumul'] = collcc20[('Total', '')].cumsum()
collcc20_rate = collcc20[('Total', '')]['2019-01':'2019-04'].mean()
collcc20_ext_vals = np.arange(collcc20['cumul'][:'2019-05'].max(), 5199423, collcc20_rate)
collcc20_ext = pd.DataFrame({'acqdate': ext_dates, 'Strips':collcc20_ext_vals})
collcc20_ext.set_index('acqdate', inplace=True)

# DG Archive cc50
collcc50 = dfs['DG_cc50']['agg'][('Total','')].to_frame()
collcc50['cumul'] = collcc50[('Total', '')].cumsum()
collcc50_rate = collcc50[('Total', '')]['2019-01':'2019-04'].mean()
collcc50_ext_vals = np.arange(collcc50['cumul'][:'2019-05'].max(), 6721266, collcc50_rate)
collcc50_ext = pd.DataFrame({'acqdate': ext_dates, 'Strips':collcc50_ext_vals})
collcc50_ext.set_index('acqdate', inplace=True)


## Plot
fig2, ax2 = plt.subplots(nrows=1, ncols=1)
linewidth = 2
# Onhand
oh['cumul'][:'2019-05'].plot(ax=ax2, color='r', legend=False, linewidth=linewidth, x_compat=True)
ext.plot(ax=ax2, style='--', color='r', label='On hand', legend=False, linewidth=linewidth, x_compat=True)
# Total Archive
collect['cumul'][:'2019-05'].plot(ax=ax2, color='b', legend=False, linewidth=linewidth, x_compat=True)
coll_ext.plot(ax=ax2, style='--', color='b', legend=False, linewidth=linewidth, x_compat=True)
# cc20
collcc20['cumul'][:'2019-05'].plot(ax=ax2, color='g', legend=False, linewidth=linewidth, x_compat=True)
collcc20_ext.plot(ax=ax2, style='--', color='g', legend=False, linewidth=linewidth, x_compat=True)
# cc50
collcc50['cumul'][:'2019-05'].plot(ax=ax2, color='black', legend=False, linewidth=linewidth, x_compat=True)
collcc50_ext.plot(ax=ax2, style='--', color='black', legend=False, linewidth=linewidth, x_compat=True)


## Formatting
years = mdates.YearLocator(2)
ax2.set_xlim('2002-01-01', '2024-01-01')
ax2.xaxis.set_major_locator(years)
plt.setp(ax2.xaxis.get_majorticklabels(), 'rotation', 90)
ax2.set(xlabel='')
ax2.set(ylabel='Total Number of Strips')
formatter = FuncFormatter(y_fmt)
ax2.yaxis.set_major_formatter(formatter)

handles, labels = ax2.get_legend_handles_labels()
handles = handles[0::2]
handles = [handles[1], handles[3], handles[2], handles[0]]
labels = labels[0::2]
labels = ['DG Archive: all cloud cover %', 'DG Archive: cloud cover 0-50%', 'DG Archive: cloud cover 0-20%', 'PGC On Hand']
fig2.legend(handles, labels, loc=(0.125, 0.75), ncol=1)
#plt.tight_layout()
#plt.gcf().text(0.01, 0.02, 'DG Archive '.format(n),
#        ha='left',
#        va='center',
#        fontstyle='italic',
#        fontsize='small')
