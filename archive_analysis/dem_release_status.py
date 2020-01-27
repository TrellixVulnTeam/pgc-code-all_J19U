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


def determine_antarctic_season(date_col):
    """
    Takes a pd.datetime date column of a pandas dataframe and 
    returns the season
    pole: 'arctic' or 'antarctic'
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


def determine_arctic_season(date_col):
    """
    Takes a pd.datetime date column of a pandas dataframe and 
    returns the season
    """
    # Convert to datetime if not already
    if type(date_col) != pd._libs.tslibs.timestamps.Timestamp:
        date_col = pd.to_datetime(date_col)
#        print('converted to dtime')
    year = date_col.year
    return year


### Load and prep data
def load_src_fp(region, stereo_type, max_date_diff=None):
    '''
    Load the given region and type as a geodataframe.
    region: 'rema' or 'arcticdem'
    stereo_type: 'intrack' or 'xtrack'
    '''
    ## Params for each region
    # Project name for xtrack source footprint selection
    # where: SQL clause to reduce intial load of source. sjoin 
    # with region for final selection
    regions = {'rema': {'project':'REMA', 'project': 'REMA', 'where':'y1 < -45'},
               'arcticdem': {'project':'ArcticDEM', 'project': 'ArcticDEM', 'where':'y1 > 45'},
               }
    ## Params for stereo type
    # src: name of danco layer for each type
    stereo_types = {'intrack': {'src': 'dg_imagery_index_stereo_cc20', 'where':regions[region]['where']},
                    'xtrack': {'src': 'dg_imagery_index_xtrack_cc20', 'where':"project = '{}'".format(regions[region]['project'])},
                    }
    
    src = query_footprint(stereo_types[stereo_type]['src'], where=stereo_types[stereo_type]['where'])
    src['type'] = stereo_type
    
    if stereo_type == 'intrack':
        src['area_sqkm'] = src['sqkm_utm']
    elif stereo_type == 'xtrack':
        src = src[src['datediff'] <= max_date_diff]
        src = area_calc(src, area_col='area_sqkm')
        src = src[src['area_sqkm'] > 500]
        src.rename(columns={'acqdate1': 'acqdate'}, inplace=True)
        
    pole = query_footprint('pgc_earthdem_regions', where="project = '{}'".format(regions[region]['project']))
    
    cols = list(src)
    
    ## Do sjoin to region to keep only relevant footprints from source, keep original columns only
    src = gpd.sjoin(src, pole, how='left')
    src = src.reindex(columns=cols)

    ## Convert date to datetime for season determination and plotting
    src['acqdate'] = pd.to_datetime(src['acqdate'])

    ## Add season info
    if region == 'rema':
        src['season'] = src.apply(lambda x: determine_antarctic_season(x['acqdate'], pole='antarctic'), axis=1)
    elif region == 'arcticdem':
        src['season'] = src.apply(lambda x: determine_arctic_season(x['acqdate'], pole='arctic'), axis=1)
    
    return src


def determine_status(src, region):
    '''
    Determine release status by using danco strip index for relevent product.
    region: 'rema' or 'arcticdem'
    '''
    
    strip_index = {'rema': 'esrifs_rema_strip_index',
               'arcticdem': 'esrifs_arcticdem_strip_index'}
    
    released_ids = list(query_footprint(strip_index[region], db='products', columns=['pairname'])['pairname'])
    
    src['released'] = np.where(src['pairname'].isin(released_ids), 'released', 'unreleased')

#########
    
print('Loading data')
## Load intrack and xtrack
it = query_footprint('dg_imagery_index_stereo_cc20', where="y1 > 45", columns=['pairname', 'acqdate', 'sqkm_utm'])
it['type'] = 'intrack'
# Copy intrack area col to align names with xtrack area col
it['area_sqkm'] = it['sqkm_utm'] 

xt = query_footprint('dg_imagery_index_xtrack_cc20', 
                     where="project = 'REMA'", 
                     columns=['pairname', 'acqdate1', 'datediff'])
xt['type'] = 'cross-track'
xt = xt[xt['datediff'] <= 10]
# Calc area of xtrack and combine utm area col with polar area col
xt = area_calc(xt)
xt['area_sqkm'] = np.where(xt['area_sqkm'].isna(), xt.polar_area, xt['area_sqkm'])

## Rename xtrack columns to align with intrack names
xt.rename(columns={'acqdate1': 'acqdate'}, inplace=True)


# Load regions
ant = query_footprint('pgc_polar_regions', where="loc_name = 'Antarctica'", columns=['loc_name'])
arc = query_footprint('pgc_polar_regions', where="loc_name = 'Arctic'", columns=['loc_name'])

print('Performing sjoin')
## Do sjoin, first saving original cols
it_cols = list(it)
xt_cols = list(xt)
it = gpd.sjoin(it, arc, how='inner')[it_cols]
xt = gpd.sjoin(xt, arc, how='inner')[xt_cols]

date_col = 'acqdate'
it[date_col] = pd.to_datetime(it[date_col])
xt[date_col] = pd.to_datetime(xt[date_col])

it['season'] = it.apply(lambda x: determine_arctic_season(x['acqdate'],), axis=1)
xt['season'] = xt.apply(lambda x: determine_antarctic_season(x['acqdate'],), axis=1)


##########
# Use REMA/ArcticDEM danco layers to determine released not released
pole = 'arctic'
if pole == 'arctic':
    released_layer = 'esrifs_arcticdem_strip_index'
elif pole == 'antarctic':
    released_layer = 'esrifs_rema_strip_index' # not sure if name is correct
else:
    print('Unrecognized pole argument')    

# Load released pairnames as list
released = list(query_footprint(released_layer, db='products', columns=['pairname'])['pairname'])
it['released'] = np.where(it['pairname'].isin(released), 'released', 'unreleased')
xt['released'] = np.where(xt['pairname'].isin(released), 'released', 'unreleased')

###########

### Save to pkl
print('Saving to pkl')
it_pkl_p = r'E:\disbr007\imagery_archive_analysis\antarctic_dems\pkl\it_release_status_2019jul11.pkl'
xt_pkl_p = r'E:\disbr007\imagery_archive_analysis\antarctic_dems\pkl\xt_release_status.2019jul11.pkl'
it.to_pickle(it_pkl_p)
xt.to_pickle(xt_pkl_p)

## Read pkl
#it = pd.read_pickle(it_pkl_p)
#xt = pd.read_pickle(xt_pkl_p)


#### PLOTTING ####

def plot_seasonal_agg_it_xt(df, agg_col, agg_type, ylabel, 
                            labels=['Released Intrack', 'Released Cross-track', 'Unreleased Intrack', 'Unreleased Cross-track'],
                            barcolor=None, 
                            out_path1=None, 
                            out_path2=None):
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
    
    agg_df.unstack(level='released')[(agg_col, 'released')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, position=1, color=barcolor, width=bar_width)
    agg_df.unstack(level='released')[(agg_col, 'unreleased')].unstack().plot(kind='bar', stacked=True, ax=ax, legend=False, alpha=0.45, color=barcolor, position=0, width=bar_width)
    
    ax.yaxis.set_major_formatter(formatter)
#    ax.set(ylabel=ylabel, xlabel='Collection Season')
    ax.set_ylabel(ylabel, fontsize=MEDIUM_SIZE)
    ax.set_xlabel('Collection Season', fontsize=MEDIUM_SIZE)
    handles, _labels = ax.get_legend_handles_labels()
#    labels = 
#    labels = ['Released Intrack', 'Unreleased Intrack']
#    labels = ['Released Cross-track', 'Unreleased Cross-track']
    fig.legend(handles, labels, ncol=1, handlelength=2.5, borderpad=0.2, labelspacing=0.5, bbox_to_anchor=(0.97, 0.91))
    fig.suptitle('Arctic Stereo DEMs')
    
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
    handles, _labels = ax2.get_legend_handles_labels()
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


def plot_seasonal_agg_it(df, agg_col, agg_type, ylabel, barcolor='red', out_path=None):
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
    fig2.suptitle('Arctic Intrack Stereo DEMs')

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



## Combine intrack and xtrack
prj_path = r'E:\disbr007\imagery_archive_analysis\ArcticDEM_released_status'
projects = ['arcticdem'] #['rema', 'arcticdem']
stereo_types = ['intrack', 'xtrack']
#stereo_types = ['xtrack']

results = []
for prj in projects:
    for st in stereo_types:
        src = load_src_fp(prj, st, max_date_diff=10)
        determine_status(src, prj)
        src.to_pickle(os.path.join(prj_path, 'pkl', '{}_{}_status.pkl'.format(prj, st)))
        results.append(src)
        
stereo = pd.concat(results, ignore_index=True)


agg_df = plot_seasonal_agg_it_xt(stereo, 'area_sqkm', 'sum', ylabel='Area km\u00b2')
agg_df = plot_seasonal_agg_it_xt(results[0], 'pairname', 'count', labels=['Released Intrack', 'Unreleased Intrack'], barcolor='red', ylabel='Area km\u00b2')
agg_df = plot_seasonal_agg_it_xt(results[1], 'pairname', 'count', labels=['Released Cross-track', 'Unreleased Cross-track'],barcolor='blue', ylabel='Area km\u00b2')
#plot_seasonal_agg_it(results[0], 'pairname', 'count', ylabel='Number of Stereo DEMs')

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

