# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 11:09:06 2019

@author: disbr007
"""

import copy
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as plticker
import matplotlib.dates as mdates
import numpy as np


plt.style.use('ggplot')

SMALL_SIZE = 8
MEDIUM_SIZE = 18
BIGGER_SIZE = 24

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=SMALL_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=SMALL_SIZE)  # fontsize of the figure title


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


#### Plot by month function start
def plot_timeseries_agg(df, date_col, id_col, freq, ax=None):
    dfc = copy.deepcopy(df)
    dfc[date_col] = pd.to_datetime(dfc[date_col])
    dfc.set_index(date_col, inplace=True)
    agg = {id_col: 'count'}
    
    dfc_agg = dfc.groupby(pd.Grouper(freq=freq)).agg(agg)
    
    ## Plotting
    # Formatting
    formatter = FuncFormatter(y_fmt)
    
    if ax is None:
        fig, ax = plt.subplots(nrows=1, ncols=1)
    dfc_agg.plot.area(y=id_col, ax=ax)
    ax.yaxis.set_major_formatter(formatter)
    
    return dfc_agg
    

def plot_timeseries_stacked(df, date_col, id_col, category_col, freq, ax=None, percentage=False):
    '''
    Plots an aggregrated stacked area chart the percentrage of id_col in each category_col
    '''
    dfc = copy.deepcopy(df)
    
    #### Aggregate by freq
    dfc[date_col] = pd.to_datetime(dfc[date_col])
    dfc.set_index(date_col, inplace=True)
    agg = {id_col: 'count'}
    dfc_agg = dfc.groupby([pd.Grouper(freq=freq), category_col]).agg(agg)
    
    dfc_agg = dfc_agg.unstack(category_col)
    dfc_agg.columns = dfc_agg.columns.droplevel()
    ## Remove NaNs
    dfc_agg.fillna(value=0, inplace=True)
    
    if ax is None:
        fig, ax = plt.subplots(nrows=1, ncols=1)
    if percentage == True:
        percent = dfc_agg.apply(lambda x: x / x.sum(), axis=1) * 100
        percent.plot.area(ax=ax)
    else:
        dfc_agg.plot.area(ax=ax)
        percent = None
    ax.xaxis.set_ticks(pd.date_range(dfc_agg.index.min(), dfc_agg.index.max(), freq='M'))
    plt.setp(ax.xaxis.get_majorticklabels(), 'rotation', 90)
    plt.setp(ax.xaxis.get_minorticklabels(), 'rotation', 90)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(3))
    
    return dfc_agg, percent
    

def plot_cloudcover(df, cloudcover_col, ax=None):
    """
    Plots cloudcover histogram.
    """
    df.hist(column=cloudcover_col, edgecolor='white', ax=ax)
