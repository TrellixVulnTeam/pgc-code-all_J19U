# -*- coding: utf-8 -*-
"""
Created on Fri May 10 09:04:28 2019

@author: disbr007
Analysis of cloud cover distribution of DG archive and imagery not on hand at PGC
"""

#import geopandas as gpd
#import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
from matplotlib.ticker import FuncFormatter


import math, os, sys

sys.path.insert(0,'C:\code\misc_utils')
from id_parse_utils import write_ids
from query_danco import query_footprint, stereo_noh


def number_formatter(x, pos):
    'The two args are the value and tick position'
    magnitude = 0
    while abs(x) >= 1000:
        magnitude += 1
        x /= 1000.0
    if magnitude == 1:
       return '%.0f%s' % (x, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    else:
        return '%.1f%s' % (x, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
#    return '%1.1f' % (x*1e-6)


def human_format(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
#    return '%.1f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    return '%.1f' % (num)


def order_magnitude(number):
    return math.floor(math.log(number, 10))


def region_loc(y1):
    # Determine region based on y coordinate
    if y1 >= -90.0 and y1 < -60.0:
        region = 'Antarctic'
    elif y1 <= 90.0 and y1 > 60.0:
        region = 'Arctic'
    elif y1 >= -60.0 and y1 < 60.0:
        region = 'Nonpolar'
    return region


## Parameters for loading data and plotting
min_cc = -1
max_cc = 20
step = 1
where = "cloudcover > {} AND cloudcover <= {}".format(min_cc, max_cc)

## Load data
print('Loading DG archive...')
dg_archive = stereo_noh(where=where, cc20=False)

# Identify region roughly - by latitude (-60; -60 - 60; +60)
dg_archive['region'] = dg_archive.y1.apply(region_loc)


'''
## Create shapefile 
print('Writing shapefile...')
driver = 'ESRI Shapefile'
out_path = 'E:\disbr007\imagery_archive_analysis\cloudcover'
out_name = 'dg_archive_stereo'
dg_archive.to_file(os.path.join(out_path, '{}_cc{}_{}.shp'.format(out_name, min_cc, max_cc)), driver=driver)


## Plotting
print('Plotting...')
bins = [x for x in range(min_cc+step, max_cc+step+step, step)]

with plt.style.context('seaborn-darkgrid', after_reset=True):
    #fig, (ax1, ax2) = plt.subplots(figsize=(10,5),nrows=1, ncols=2, sharey=True)
    fig, ax1 = plt.subplots(figsize=(9,5),nrows=1, ncols=1)
    #fig.suptitle('DG Archive Analysis: Cloudcover', fontsize=16)
    
    ax1.hist([dg_archive[(dg_archive['y1'] > low) & (dg_archive['y1'] <= high)].cloudcover for low, high in [(-90, -60), (-60, 60), (60, 90)]], 
                  label=['Antarctic', 'Nonpolar', 'Arctic'], stacked=True, rwidth=1.0, bins=bins, align='left', edgecolor='white')
    
    platforms = sorted(list(dg_archive.platform.unique()))
    #ax2.hist([dg_archive[dg_archive.platform==platform].cloudcover for platform in platforms], label=platforms, stacked=True, rwidth=1.0, bins=bins)
    
    #for ax in (ax1, ax2):
    for ax in [ax1]:
        # Add annotation for each bar
        counts, the_bins = np.histogram(dg_archive.cloudcover, bins=bins)
        for b, count in zip(the_bins, counts):
            ax.annotate('{}'.format(human_format(count)), xy=(b, count), xytext=(0,2), textcoords='offset points', 
                    ha='center', va='bottom', fontsize=7)
        
        ## Format y axes to precision and units appropriate
        formatter = FuncFormatter(number_formatter) # create formatter (eg. 1.0M)
        ax.yaxis.set_major_formatter(formatter) # apply formatter
        
        ## Set y, x axis tick intervals, limits, labels
        start, end = ax.get_ylim()
        ystep = 10**(order_magnitude((end-start)))
        ax.yaxis.set_ticks(np.arange(start, end+ystep, ystep))
        
        ax.xaxis.set_ticks(np.arange(min_cc+step, max_cc+step, step))
        start, end = ax.get_xlim()
        ax.set_xlim(xmin=min_cc, xmax=max_cc+step)
        ax.set(xlabel='Cloudcover %')

        ax.legend()
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], labels[::-1])
        
    ax1.set(ylabel='Number of IDs')
    ax1.set_title('Cloudcover by Region')  
    #ax2.set_title('Cloudcover by Platform')
    plt.gcf().text(0.01, 0.02, 'Analysis of stereo archive not on hand at PGC', 
           ha='left', 
           va='center', 
           fontstyle='italic',
           fontsize='small')
    plt.tight_layout()
    fig.show()
'''