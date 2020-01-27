# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 15:36:04 2020

@author: disbr007
Create a summary of input selection from danco table (add support for mfp table)
"""
import copy

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


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


def det_cc_cat(x):
    if x <= 20:
        cc_cat = 'cc20'
    elif x <= 30:
        cc_cat = 'cc21-30'
    elif x <= 40:
        cc_cat = 'cc31-40'
    elif x <= 50:
        cc_cat = 'cc41-50'
    else:
        cc_cat = 'over_50'
    
    return cc_cat


# table = copy.deepcopy(noh_fps)

def summarize_danco_fp(fp):
    
    table = copy.deepcopy(fp)
    
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(1,2)
    
    # Count unique catalogids
    num_unique_ids = len(table.catalogid.unique())
    
    # Monthly histograms
    table['acqdate'] = pd.to_datetime(table['acqdate'])
    monthly = table.set_index('acqdate')
    # By sensor
    agg = {'catalogid': 'nunique'}
    monthly_platform = monthly.groupby([pd.Grouper(freq='M'), 'platform']).agg(agg)
    monthly_platform.unstack().plot.area(ax=ax1)
    # Fix legend labels
    handles, labels = ax1.get_legend_handles_labels()
    labels = [l.replace("(catalogid, ", "") for l in labels]
    labels = [l.replace(")", "") for l in labels]
    ax1.legend(handles, labels)
    ax1.set(title='Platforms')
    
    # Cloudcover histogram
    table['cc_cat'] = table['cloudcover'].apply(lambda x: det_cc_cat(x))
    monthly_cc = monthly.groupby([pd.Grouper(freq='M'), 'cc_cat']).agg(agg)
    monthly_cc.unstack().plot.area(ax=ax2)
    handles, labels = ax2.get_legend_handles_labels()
    labels = [l.replace("(catalogid, ", "") for l in labels]
    labels = [l.replace(")", "") for l in labels]
    ax2.legend(handles, labels)
    ax2.set(title='Cloudcover')

# Stereo / mono pie chart
