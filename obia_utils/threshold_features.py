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
slope_thresh = 15
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
logger.info('Loaded {} segments...'.format(len(seg)))

## Find segments in predrawn thermokarst boundaries
tks = gpd.read_file(tks_bounds_p)
tks = tks[tks['obs_year']==2015]

## Select only those features within segmentation bounds
xmin, ymin, xmax, ymax = seg.total_bounds
tks = tks.cx[xmin:xmax, ymin:ymax]


# This allows lists to be placed in cells
# seg = seg.astype(object)


def get_neighbors(gdf, subset=None, unique_id=None, neighbor_field='neighbors'):
    """
    Gets the neighbors for a subset of a polygon geometry
    geodataframe, optionally only a subset.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to compute neighbors in.
    subset : gpd.GeoDataFrame
        Selected rows from gdf to compute neighbors for. Highly recommended 
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
    nebs = pd.DataFrame({unique_id:labels, neighbor_field:ns})
    # Combine the neighbors dataframe back into the main dataframe
    result = pd.merge(gdf,
                      nebs,
                      how='left',
                      on='label')
    logger.info('Neighbor computation complete.')
    
    return result


# def get_value(df, lookup_field, lookup_value, value_field):
#     val = df[df[lookup_field]==lookup_value][value_field]
#     if len(val) == 0:
#         logger.error('Lookup value not found: {} in {}'.format(lookup_value, lookup_field))
#     elif len(val) > 1:
#         logger.error('Lookup value occurs more than once: {} in {}'.format(lookup_value, lookup_field))
    
#     return val.values[0]
        

def neighbor_values(df, unique_id, neighbors, value_field):
    """
    Look up the values of a list of neighbors. Returns dict of id:value
    
    Parameters
    ----------
    df : pd.DataFrame
        Dataframe to look up values in
    unique_id : str
        Name of field in df with unique values and field where neighbor values are found
    neighbors : list
        List of unique_id's to get values of
    value_field : str
        Name of field to return values from.
    
    Returns
    -------
    dict : unique_id of neighbor : value_field value
    
    """
    values = {n:df[df[unique_id]==n][value_field].values[0] for n in neighbors}
    
    return values
    

def neighbor_adjacent(gdf, subset, unique_id,
                      adjacent_field='adj_thresh',
                      neighbor_field='neighbors', 
                      value_field=None, value_thresh=None, value_compare=None):
    
    """
    For each feature in subset, determines if it is adjacent to feature meeting "value" requirements.
    For example, is the feature adjacent to another feature with a mean_slope > 10.
    
    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to find adjacent features in.
    subset : gpd.GeoDataFrame
        Selected rows from gdf to compute adjacency for. Highly recommended 
        for large dataframes as neighbor computation can be slow.
    unique_id : str
        Unique field name in gdf and subset to use as identifier.
    adjacent_field : str
        Name of field to create to hold Boolean output of whether feature meets adjacent reqs.
    neighbor_field : str
        Name of field to create to hold neighbors, temporary.
    value_field : str
        Name of field to use in evaluating adjacent threshold.
    value_thresh : int/float/str
        Value of value field to use in threshold.
    value_compare : str
        The operator to use to compare feature value to value thresh. One of ['<', '>', '==', '!=']
    
    Returns
    -------
    result : pd.Series
        Boolean series whether feature meets requirements of adjacency or not.

    """
    # Find the IDs of all the features in subset, store in neighbor field
    gdf = get_neighbors(gdf, subset=subset, unique_id=unique_id,
                        neighbor_field=neighbor_field)
    # Use all of the IDs in subset to pull out unique_ids and their neighbor lists
    subset_ids = subset[unique_id]
    neighbors = gdf[gdf[unique_id].isin(subset_ids)][[unique_id, neighbor_field]]
    
    # Iterate over features and check if any meet threshold
    logger.info('Finding adjacent features that meet threshold...')
    have_adj = []
    for index, row in tqdm(neighbors.iterrows(), total=len(neighbors)):
        values = neighbor_values(gdf, unique_id, row[neighbor_field], value_field)
        ## Assuming value compare operator is less than for testing
        matches = [v < value_thresh for k, v in values.items()]
        if any(matches):
            have_adj.append(row[unique_id])
        # match_neighbs.extend(matches)
    
    # If feature had neighbor meeting threshold, return True, else False
    gdf[adjacent_field] = gdf[unique_id].isin(have_adj)
    
    return gdf



seg[steep] = seg[slope_mean] > slope_thresh

# seg = get_neighbors(seg, subset=seg[seg['steep']==True], 
#                     unique_id=unique_id,
#                     neighbor_field=neighb)

x = neighbor_adjacent(seg, subset=seg[seg['steep']==True],
                      unique_id=unique_id,
                      neighbor_field=neighb,
                      value_field=tpi41_mean,
                      value_thresh=tpi41_thresh,
                      value_compare='<')

# x['headwall'] == 
# # #### Merge features
# # Create subset of features to be merged
# min_area = 50
# seg[merge] = seg.geometry.area < min_area
# subset = seg[seg[merge]==True]

# x = get_neighbors(seg, subset=subset, unique_id=unique_id)
# for index, row in x.iterrows():
#     if row[merge] == True:

#### Plotting
# Set up
plt.style.use('ggplot')
fig, ax = plt.subplots(1,1, figsize=(10,10))
fig.set_facecolor('darkgray')
ax.set_yticklabels([])
ax.set_xticklabels([])

# Plot full segmentation with no fill
seg.plot(facecolor='none', linewidth=0.5, ax=ax, edgecolor='grey')
# Plot the classified features
seg[seg[steep]==True].plot(facecolor='b', alpha=0.76, ax=ax)
x[x['adj_thresh']==True].plot(facecolor='r', ax=ax)
# Plot the digitized RTS boundaries
tks.plot(facecolor='none', edgecolor='yellow', linewidth=1, ax=ax)
plt.tight_layout()



