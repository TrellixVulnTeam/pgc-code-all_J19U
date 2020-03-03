# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:50:31 2020

@author: disbr007
"""

import logging.config
import os
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)


# Parameters
# Field names
# Created
merge = 'merge'
# Existing
unique_id = 'label'


# Inputs
seg_path = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_clip_ms_lsms_sr5rr200ss400_stats.shp'
tks_bounds_p = r'E:\disbr007\umn\ms\shapefile\tk_loc\digitized_thaw_slumps.shp'

# Load data
seg = gpd.read_file(seg_path)
tks = gpd.read_file(tks_bounds_p)
logger.info('Loaded {} segments...'.format(len(seg)))

## Find segments in predrawn thermokarst boundaries
tks = gpd.read_file(tks_bounds_p)
tks = tks[tks['obs_year']==2015]

## Select only those features within segmentation bounds
xmin, ymin, xmax, ymax = seg.total_bounds
tks = tks.cx[xmin:xmax, ymin:ymax]


# This allows lists to be placed in cells
# seg = seg.astype(object)


def get_neighbors(gdf, subset=None, unique_id=None, neighbor_fld='neighbors'):
    """
    Gets the neighbors for a subset of a polygon geometry
    geodataframe, optionally only a subset.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to compute neighbors in..
    subset : gpd.GeoDataFrame
        Selection from gdf to compute neighbors for. Highly recommended 
        for large dataframes as neighbor computation can be slow.
    unique_id : str
        Unique field name in gdf and subset to use as identifier. The default is None.

    Returns
    -------
    result : gpd.GeoDataFrame
        GeoDataFrame with added column containing list of unique IDs of neighbors.

    """
    
    # If no subset is provided, use the whole dataframe
    if subset is None:
        subset = gdf
    
    # List to store neighbors
    ns = []
    # List to store unique_ids
    labels = []
    # Iterate over rows, for each row, get unique_ids of all features it touches
    logger.info('Getting neighbors for {} features...'.format(len(subset)))
    for index, row in tqdm(subset.iterrows(), total=len(subset)):
        neighbors = seg[seg.geometry.touches(row['geometry'])][unique_id].tolist() 
        if row[unique_id] in neighbors:
            neighbors = neighbors.remove(row[unique_id])
        
        # Save the neighbors that have been found and their IDs
        ns.append(neighbors)
        labels.append(row[unique_id])

    # Create data frame of the unique ids and their neighbors
    nebs = pd.DataFrame({unique_id:labels, neighbor_fld:ns})
    # Combine the neighbors dataframe back into the main dataframe
    result = pd.merge(gdf,
                      nebs,
                      how='left',
                      on='label')
    logger.debug('Neighbor computation complete.')
    
    return result


# x = get_neighbors(seg, subset=subset, unique_id=unique_id)


# # #### Merge features
# # Create subset of features to be merged
# min_area = 50
# seg[merge] = seg.geometry.area < min_area
# subset = seg[seg[merge]==True]

# x = get_neighbors(seg, subset=subset, unique_id=unique_id)
# for index, row in x.iterrows():
#     if row[merge] == True:


plt.style.use('ggplot')
fig, axes = plt.subplots(2, 3, figsize=(16,6))
axes = axes.flatten()
slopes = [-3, -2, -1, 1, 2, 3]
# slope_thresh = 9
for i, thresh in enumerate(slopes):
    ax = axes[i]
    ax.set_title(thresh)
    seg['thresh'] = seg['tpi81_mean'] < thresh
    seg.plot(column='thresh', alpha=0.75, ax=ax, cmap='bwr')
    seg.plot(facecolor='none', linewidth=0.5, ax=ax, edgecolor='white')
    tks.plot(facecolor='none', edgecolor='black', linewidth=2, ax=ax)
    plt.tight_layout()



