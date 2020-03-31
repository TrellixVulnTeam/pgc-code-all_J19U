# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:50:31 2020

@author: disbr007
"""

# import logging.config
# import os
import matplotlib.pyplot as plt
import numpy as np
# from random import randint
# from tqdm import tqdm

import pandas as pd
import geopandas as gpd
# from osgeo import gdal, gdalconst, ogr


from misc_utils.logging_utils import create_logger, create_module_loggers
# from obia_utils import neighbor_adjacent, mask_class, neighbor_features
from obia_utils.obia_utils import neighbor_adjacent, mask_class, neighbor_features


logger = create_logger(__name__, 'sh', 'INFO')
module_loggers = create_module_loggers('sh', 'INFO')


# Parameters
slope_thresh = 5
tpi_low_thresh = -0.6 # value threshold for tpi_mean field
tpi_high_thresh = 0.4
ndvi_thresh = 0.0


# tpis_low = [-0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -0.9, -1]
# tpis_high = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]

# Field names
# Created
merge = 'merge'
steep = 'steep' # features above slope threshold
neighb = 'neighbors' # field to hold neighbor unique ids
headwall = 'headwall' # field - bool - headwall = True
adj_low_tpi_field = 'alt{}'.format(str(tpi_low_thresh).replace('.', 'x').replace('-', 'neg'))
adj_high_tpi_field = 'aht{}'.format(str(tpi_high_thresh).replace('.', 'x'))
ndvi_thresh_field = 'ndvi{}'.format(str(ndvi_thresh).replace('.', 'x').replace('-', 'neg'))
# Existing
unique_id = 'label'
slope_mean = 'slope_mean'
tpi_mean = 'tpi81_mean'
ndvi_mean = 'ndvi_mean'

# Inputs
# 2015 Slope
# seg_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500_stats.shp'
# 2015 Imagery
seg_path = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_clip_ms_lsms_sr5rr200ss400_stats.shp'
tks_bounds_p = r'E:\disbr007\umn\ms\shapefile\tk_loc\digitized_thaw_slumps.shp'

# Load data
logger.info('Loading segmentation...')
seg = gpd.read_file(seg_path)
tks = gpd.read_file(tks_bounds_p)
logger.info('Loaded {} segments.'.format(len(seg)))

# Load digitzed thermokarst boundaries
tks = gpd.read_file(tks_bounds_p)
tks = tks[tks['obs_year']==2015]
# Select only those thermokarst features within segmentation bounds
xmin, ymin, xmax, ymax = seg.total_bounds
tks = tks.cx[xmin:xmax, ymin:ymax]

# Determine features above steepness threshold
seg[steep] = seg[slope_mean] > slope_thresh

# Steep and adjacent to tpi < tpi_low_param and tpi > tpi_high_param
seg = neighbor_adjacent(seg, subset=seg[seg['steep']==True],
                        unique_id=unique_id,
                        neighbor_field=neighb,
                        adjacent_field=adj_low_tpi_field,
                        value_field=tpi_mean,
                        value_thresh=tpi_low_thresh,
                        value_compare='<')

seg = neighbor_adjacent(seg, subset=seg[seg['steep']==True],
                        unique_id=unique_id,
                        neighbor_field=neighb,
                        adjacent_field=adj_high_tpi_field,
                        value_field=tpi_mean,
                        value_thresh=tpi_high_thresh,
                        value_compare='>')

# Steeo and adjacent to NDVI < ndvi_thresh
seg = neighbor_adjacent(seg, subset=seg[seg['steep']==True],
                        unique_id=unique_id,
                        neighbor_field=neighb,
                        adjacent_field=ndvi_thresh_field,
                        value_field=ndvi_mean,
                        value_thresh=ndvi_thresh,
                        value_compare='<')

# seg[headwall] = np.where(seg['adj_low_tpi'] & seg['adj_high_tpi'], True, False)
# seg.drop(columns=[neighb]).to_file(r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500_stats_nbs.shp')


## Get neighbors as shp
# subset = seg[seg[steep]==True]
# neighbor_df = neighbor_features(unique_id=unique_id, gdf=seg, subset=subset,
#                                 neighbor_ids_col=neighb)
    

### Remove class from segmentation
# seg['h1'] = np.where(seg[headwall]==True, 1, 0)
# # # Raster to be segmented
# img_p = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\slope\WV02_20150906_pcatdmx_slope_a6g.tif'
# out = mask_class(seg, 'h1', img_p, r'/vsimem/test_raster.vrt', mask_value=1)


### Plotting
# Set up
plt.style.use('ggplot')
fig, axes = plt.subplots(2,2, figsize=(10,10))
fig.set_facecolor('darkgray')

axes=axes.flatten()


# Plot full segmentation with no fill
for ax in axes:
    seg.plot(facecolor='none', linewidth=0.5, ax=ax, edgecolor='grey')
    # Plot the digitized RTS boundaries
    tks.plot(facecolor='none', edgecolor='black', linewidth=2, ax=ax)
    ax.set_yticklabels([])
    ax.set_xticklabels([])

# ax = axes[0]

# Plot the classified features
axes[0].set_title(steep)
seg[seg[steep]==True].plot(facecolor='y', alpha=0.75, ax=axes[0])
# seg[seg[headwall]==True].plot(facecolor='r', ax=ax, alpha=0.5)
# Plot cols
axes[1].set_title(adj_low_tpi_field)
seg[seg[adj_low_tpi_field]==True].plot(facecolor='b', alpha=0.75, ax=axes[1])

axes[2].set_title(adj_high_tpi_field)
seg[seg[adj_high_tpi_field]==True].plot(facecolor='r', alpha=0.75, ax=axes[2])

axes[3].set_title(ndvi_thresh_field)
seg[seg[ndvi_thresh_field]==True].plot(facecolor='g', alpha=0.75, ax=axes[3])

plt.tight_layout()
