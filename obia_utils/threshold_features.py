# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:50:31 2020

@author: disbr007
"""

import logging.config
# import os
import matplotlib.pyplot as plt
# import numpy as np
# from tqdm import tqdm

# import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import LOGGING_CONFIG
from obia_utils import neighbor_adjacent

logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)
for m in ['obia_utils']:
    logger2 = logging.getLogger(m)


# Parameters
slope_thresh = 11.5
# Field names
# Created
merge = 'merge'
steep = 'steep' # features above slope threshold
neighb = 'neighbors' # field to hold neighbor unique ids
tpi41_thresh = -1 # value threshold for tpi41_mean field
# Existing
unique_id = 'label'
slope_mean = 'slope_mean'
tpi41_mean = 'tpi41_mean'


# Inputs
seg_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500_stats.shp'
tks_bounds_p = r'E:\disbr007\umn\ms\shapefile\tk_loc\digitized_thaw_slumps.shp'

# Load data
logger.info('Loading segmentation...')
seg = gpd.read_file(seg_path)
tks = gpd.read_file(tks_bounds_p)
logger.info('Loaded {} segments.'.format(len(seg)))

## Find segments in predrawn thermokarst boundaries
tks = gpd.read_file(tks_bounds_p)
tks = tks[tks['obs_year']==2015]

## Select only those features within segmentation bounds
xmin, ymin, xmax, ymax = seg.total_bounds
tks = tks.cx[xmin:xmax, ymin:ymax]


# This allows lists to be placed in cells
# seg = seg.astype(object)






seg[steep] = seg[slope_mean] > slope_thresh


seg = neighbor_adjacent(seg, subset=seg[seg['steep']==True],
                        unique_id=unique_id,
                        neighbor_field=neighb,
                        value_field=tpi41_mean,
                        value_thresh=tpi41_thresh,
                        value_compare='<')


#### Plotting
# Set up
plt.style.use('ggplot')
fig, ax = plt.subplots(1,1, figsize=(10,10))
fig.set_facecolor('darkgray')
ax.set_yticklabels([])
ax.set_xticklabels([])

# Plot full segmentation with no fill
seg.plot(facecolor='none', linewidth=0.5, ax=ax, edgecolor='grey')
# Plot the digitized RTS boundaries
tks.plot(facecolor='none', edgecolor='black', linewidth=2, ax=ax)
# Plot the classified features
# seg[seg[steep]==True].plot(facecolor='b', alpha=0.75, ax=ax)
seg[seg['adj_thresh']==True].plot(facecolor='r', ax=ax, alpha=0.5)


plt.tight_layout()



