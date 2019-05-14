# -*- coding: utf-8 -*-
"""
Created on Fri May 10 09:04:28 2019

@author: disbr007
Analysis of cloud cover distribution of DG archive and imagery not on hand at PGC
"""

#import geopandas as gpd
#import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
from matplotlib.ticker import FuncFormatter
import math, os

from query_danco import query_footprint


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
    return '%.1f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def order_magnitude(number):
    return math.floor(math.log(number, 10))


def region_loc(y1):
    # Add region column based on y coordinate
    regions = {
        'Antarctica': (-90.1, -60.0),
        'Nonpolar': (-60.0, 60.0),
        'Arctic': (60.0, 90.1)
        }
    for key, value in regions.items():
        if y1 > value[0] and y1 < value[1]:
           region = key
        else:
            region = 'unk'
    return region


## Parameters for loading data and plotting
min_cc = 21
max_cc = 30
step = 1 

## Load data
# Get all PGC IDs
pgc_archive = query_footprint(layer='pgc_imagery_catalogids', table=True)
pgc_ids = list(pgc_archive.catalog_id)
del pgc_archive

# Get all DG ids in index table (no geometry)
print('Loading DG archive...')
dg_archive = query_footprint(layer='index_dg', where="cloudcover >= {} AND cloudcover <= {}".format(min_cc, max_cc), table=True)

# Get only DG ids not in PGC index
dg_archive = dg_archive[~dg_archive.catalogid.isin(pgc_ids)]

# Identify region roughly - by latitude (-60; -60 - 60; +60)
dg_archive['region'] = dg_archive.y1.apply(region_loc)

## Create shapefile of ids not on hand from 20.01% cloudcover to 30%
# Reduce to just 20-30% - not neccessary if only 20-30% loaded
dg_archive_cc20_30 = dg_archive[(dg_archive.cloudcover > 20) & (dg_archive.cloudcover < 30)]
dg_archive_cc20_30_ids = list(dg_archive_cc20_30.catalogid)

# Load geometries for 20-30% ids
print('Loading ids not on hand with geometries...')
dg_geoms = query_footprint(layer='index_dg', where="catalogid in ('{}')".format("','".join(dg_archive_cc20_30_ids)))

driver = 'ESRI Shapefile'
out_path = 'E:\disbr007\imagery_archive_analysis\cloudcover'
dg_geoms.to_file(os.path.join(out_path, 'dg_archive_cc20_30.shp'), driver=driver)
dg_geoms[(dg_geoms.cloudcover > 20) & (dg_geoms.cloudcover <= 21)].to_file(os.path.join(out_path, 'dg_archive_cc20_21.shp'), driver=driver)
dg_geoms[(dg_geoms.cloudcover > 20) & (dg_geoms.cloudcover <=25)].to_file(os.path.join(out_path, 'dg_archive_cc20_25.shp'), driver=driver)

## Plotting
bins = [x for x in range(min_cc, max_cc+step, step)]

plt.style.context('ggplot')
#fig, (ax1, ax2) = plt.subplots(figsize=(10,5),nrows=1, ncols=2, sharey=True)
fig, ax1 = plt.subplots(figsize=(9,5),nrows=1, ncols=1)
#fig.suptitle('DG Archive Analysis: Cloudcover', fontsize=16)

ax1.hist([dg_archive[(dg_archive['y1'] > low) & (dg_archive['y1'] <= high)].cloudcover for low, high in [(-90, -60), (-60, 60), (60, 90)]], 
              label=['Antarctica', 'Nonpolar', 'Arctic'], stacked=True, rwidth=1.0, bins=bins)

platforms = sorted(list(dg_archive.platform.unique()))
#ax2.hist([dg_archive[dg_archive.platform==platform].cloudcover for platform in platforms], label=platforms, stacked=True, rwidth=1.0, bins=bins)

#for ax in (ax1, ax2):
for ax in [ax1]:
    counts, the_bins = np.histogram(dg_archive.cloudcover, bins=bins)
    for b, count in zip(the_bins, counts):
        ax.annotate('{}'.format(human_format(count)), xy=(b+(step/2), count), xytext=(0,2), textcoords='offset points', 
                ha='center', va='bottom', fontsize=8)
    
    ## Format axes
    formatter = FuncFormatter(number_formatter) # create formatter (eg. 1.0M)
    ax.yaxis.set_major_formatter(formatter)
    
    ## Set y, x axis tick intervals, limits, labels
    start, end = ax.get_ylim()
    ystep = 10**(order_magnitude((end-start)/10))
    ax.yaxis.set_ticks(np.arange(start, end, ystep))
    ax.xaxis.set_ticks(np.arange(min_cc, max_cc+step, step))
#    start, end = ax.get_xlim()
    ax.set_xlim(xmin=min_cc, xmax=max_cc)
    ax.set(xlabel='Cloudcover %')
    ax.legend()
    
ax1.set(ylabel='Count')
ax1.set_title('Cloudcover by Region')  
#ax2.set_title('Cloudcover by Platform')
plt.gcf().text(0.01, 0.01, '*analysis of archive not on hand at PGC', ha='left', va='center')
plt.tight_layout()
fig.show()
