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
from utm_area_calc import area_calc


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


### Load and prep data
## Load intrack and xtrack
#it = query_footprint('dg_imagery_index_stereo_cc20', where="y1 < -50", columns=['pairname', 'acqdate', 'sqkm_utm'])
#it['type'] = 'intrack'
## Copy intrack area col to align names with xtrack area col
#it['area_sqkm'] = it['sqkm_utm'] 
#
#xt = query_footprint('dg_imagery_index_xtrack_cc20', 
#                     where="project = 'REMA'", 
#                     columns=['pairname', 'acqdate1', 'datediff'])
#xt['type'] = 'cross-track'
#xt = xt[xt['datediff'] <= 10]
## Calc area of xtrack and combine utm area col with polar area col
#xt = area_calc(xt)
##xt['area_m'] = np.where(xt.sqkm_utm.isna(), xt.polar_area, xt.sqkm_utm)
#
## Rename xtrack columns to align with intrack names
#xt.rename(columns={'acqdate1': 'acqdate'}, inplace=True)
#
## Load REMA pairnames as list
#rema = list(query_footprint('esrifs_rema_strip_index', db='products', columns=['pairname'])['pairname'])
#
## Load regions
#ant = query_footprint('pgc_world_aois', where="loc_name = 'Antarctica'", columns=['loc_name'])
#
### Do sjoin, first saving original cols
#it_cols = list(it)
#xt_cols = list(xt)
#it = gpd.sjoin(it, ant, how='inner')[it_cols]
#xt = gpd.sjoin(xt, ant, how='inner')[xt_cols]
#
## Use REMA to determine released not released
#it['released'] = np.where(it['pairname'].isin(rema), 'released', 'unreleased')
#xt['released'] = np.where(xt['pairname'].isin(rema), 'released', 'unreleased')
#
#date_col = 'acqdate'
#it[date_col] = pd.to_datetime(it[date_col])
#xt[date_col] = pd.to_datetime(xt[date_col])
#
#it['season'] = it.apply(lambda x: determine_season(x['acqdate']), axis=1)
#xt['season'] = xt.apply(lambda x: determine_season(x['acqdate']), axis=1)
#
#
### Save to pkl
it_pkl_p = r'E:\disbr007\imagery_archive_analysis\antarctic_dems\pkl\it_release_status_2019jul11.pkl'
xt_pkl_p = r'E:\disbr007\imagery_archive_analysis\antarctic_dems\pkl\xt_release_status.2019jul11.pkl'
#it.to_pickle(it_pkl_p)
#xt.to_pickle(xt_pkl_p)


## Read pkl
it = pd.read_pickle(it_pkl_p)
xt = pd.read_pickle(xt_pkl_p)


## Combine intrack and xtrack
stereo = pd.concat([it, xt], ignore_index=True)


def plot_seasonal_agg_it_xt(df, agg_col, agg_type, ylabel, out_path1=None, out_path2=None):
    '''
    Makes two plots, one with intrack and cross-track stacked and one with them dissolved into one
    df: unaggregated dataframe
    agg_col: name of column to aggregate
    agg_type: type of aggregation to use e.g.: sum, count, etc.
    freq: frequency to use e.g.: Y, M, D, etc.
    '''
    
    df = df[(df['acqdate'] >= '2010-07-01') & (df['acqdate'] <= '2019-06-30')]
    agg = {agg_col: agg_type}
    
    ## Plotting
    plt.style.use('ggplot')
    bar_width = 0.4
    formatter = FuncFormatter(y_fmt)
    # Font sizes
    SMALL_SIZE = 12
    MEDIUM_SIZE = 18
    BIGGER_SIZE = 24
    
    ## Plot 1: Intrack and cross-track stacked
    agg_df = df.groupby(['season', 'released', 'type']).agg(agg)
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(16, 10))
    
    agg_df.unstack(level='released')[(agg_col, 'released')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, position=1, width=bar_width)
    agg_df.unstack(level='released')[(agg_col, 'unreleased')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, alpha=0.45, position=0, width=bar_width)
    
    ax.yaxis.set_major_formatter(formatter)
#    ax.set(ylabel=ylabel, xlabel='Collection Season')
    ax.set_ylabel(ylabel, fontsize=MEDIUM_SIZE)
    ax.set_xlabel('Collection Season', fontsize=MEDIUM_SIZE)
    handles, labels = ax.get_legend_handles_labels()
    labels = ['Released Cross-track', 'Released Intrack', 'Unreleased Cross-track', 'Unreleased Intrack']
    fig.legend(handles, labels, ncol=1, handlelength=2.5, borderpad=0.2, labelspacing=0.5, bbox_to_anchor=(0.97, 0.91))
    fig.suptitle('Antarctic Stereo DEMs')
    
    plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
    plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
    plt.rc('figure', titlesize=MEDIUM_SIZE)  # fontsize of the figure title
    
    fig.tight_layout(rect=[0, 0.01, 1, 0.97])
    if out_path1:
        plt.savefig(out_path1, edgecolor='black', format='jpg', quality=100, dpi=1000)
    
    # Plot2: Intrack and cross-track dissolved
    agg_df2 = df.groupby(['season', 'released']).agg(agg)
    fig2, ax2 = plt.subplots(nrows=1, ncols=1, figsize=(16, 10))
    agg_df2.unstack(level='released')[(agg_col, 'released')].plot(kind='bar', color='green', stacked=False, 
                   ax=ax2, legend=False, position=1, width=bar_width)
    agg_df2.unstack(level='released')[(agg_col, 'unreleased')].plot(kind='bar', color='green', stacked=False, 
                   ax=ax2, legend=False, alpha=0.40, position=0, width=bar_width)
    

    ax2.yaxis.set_major_formatter(formatter)
    ax2.set(ylabel=ylabel, xlabel='Collection Season')
    handles, labels = ax2.get_legend_handles_labels()
    labels = ['Released', 'Unreleased']
    fig2.legend(handles, labels, ncol=1, handlelength=2.5, borderpad=0.2, labelspacing=0.5, bbox_to_anchor=(0.97, 0.91))
    
    fig2.suptitle('Antarctic Stereo DEMs')
    
    plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
    plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
    plt.rc('figure', titlesize=MEDIUM_SIZE)  # fontsize of the figure title
    
    fig2.tight_layout(rect=[0, 0.01, 1, 0.97])
    if out_path2:
        print('yes')
        plt.savefig(out_path2, edgecolor='black', format='jpg', quality=100, dpi=1000)
        
    return agg_df


def plot_seasonal_agg_it(df, agg_col, agg_type, barcolor, ylabel, out_path=None):
    '''
    Makes two plots, one with intrack and cross-track stacked and one with them dissolved into one
    df: unaggregated dataframe
    agg_col: name of column to aggregate
    agg_type: type of aggregation to use e.g.: sum, count, etc.
    freq: frequency to use e.g.: Y, M, D, etc.
    '''
    df = df[(df['acqdate'] >= '2010-07-01') & (df['acqdate'] <= '2019-06-30')]
    print(df.acqdate.min())
    agg = {agg_col: agg_type}
    ## Plotting
    plt.style.use('ggplot')
    bar_width = 0.4
    formatter = FuncFormatter(y_fmt)
    
    # Plot1: Intrack 
    agg_df2 = df.groupby(['season', 'released']).agg(agg)
    fig2, ax2 = plt.subplots(nrows=1, ncols=1, figsize=(16, 10))
    agg_df2.unstack(level='released')[(agg_col, 'released')].plot(kind='bar', color=barcolor, stacked=False, 
                   ax=ax2, legend=False, position=1, width=bar_width)
    agg_df2.unstack(level='released')[(agg_col, 'unreleased')].plot(kind='bar', color=barcolor, stacked=False, 
                   ax=ax2, legend=False, alpha=0.40, position=0, width=bar_width)
    
    ## Formatting
    # Font sizes
    SMALL_SIZE = 12
    MEDIUM_SIZE = 18
    BIGGER_SIZE = 24
    
    ax2.yaxis.set_major_formatter(formatter)
    ax2.set_ylabel(ylabel, fontsize=MEDIUM_SIZE)
    ax2.set_xlabel('Collection Season', fontsize=MEDIUM_SIZE)
    handles, labels = ax2.get_legend_handles_labels()
    labels = ['Released', 'Unreleased']
    fig2.legend(handles, labels, ncol=1, handlelength=2.5, borderpad=0.2, labelspacing=0.5, bbox_to_anchor=(0.97, 0.91))
    fig2.suptitle('Antarctic Intrack Stereo DEMs')

    plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
    plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
    plt.rc('figure', titlesize=MEDIUM_SIZE)  # fontsize of the figure title
        
    fig2.tight_layout(rect=[0, 0.01, 1, 0.97])
    if out_path:
        plt.savefig(out_path,
                    edgecolor='black',
                    format='jpg', quality=100, dpi=1000)
    

agg_df = plot_seasonal_agg_it_xt(stereo, 'pairname', 'count', ylabel='Number of Stereo DEMs',)
#                        out_path1=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack_xtrack\antarctic_dems_pairs.jpg",
#                       out_path2=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack_xtrack\antarctic_dems_pairs_comb.jpg")
#plot_seasonal_agg_it_xt(stereo, 'area_sqkm', 'sum', ylabel='Area km\u00b2',
#                        out_path1=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack_xtrack\antarctic_dems_area.jpg",
#                        out_path2=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack_xtrack\antarctic_dems_area_comb.jpg")

#plot_seasonal_agg_it(it, 'pairname', 'count', 
#                     barcolor='green',ylabel='Number of Intrack Stereo DEMs', 
#                     out_path=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack\antarctic_dems_intrack_pairs.jpg")
#plot_seasonal_agg_it(it, 'area_sqkm', 'sum', 
#                     barcolor='purple',ylabel='Area km\u00b2', 
#                     out_path=r"E:\disbr007\imagery_archive_analysis\antarctic_dems\intrack\antarctic_dems_intrack_area.jpg")

