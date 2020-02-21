# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:50:31 2020

@author: disbr007
"""

import logging.config
import os
import numpy as np

import pandas as pd
import geopandas as gpd
from tqdm import tqdm


from misc_utils.logging_utils import create_logger, LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)


# Parameters
# Field names
# Created
merge = 'merge'
# Existing
unique_id = 'label'

# tpi_thresh = -2
diff_thres = -1.5

# Inputs
seg_path = r'V:\\pgc\\data\\scratch\\jeff\\ms\\scratch\\aoi6_good\\seg\\WV02_20150906_clip_ms_lsms_sr5rr200ss150_stats.shp'

# Load data
seg = gpd.read_file(seg_path)
logger.info('Loaded {} segments...'.format(len(seg)))
print(seg.crs)

# This allows lists to be placed in cells
# seg = seg.astype(object)
print(seg.crs)


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


# subset = seg[seg['diff_mean'] < diff_thres]

# x = get_neighbors(seg, subset=subset, unique_id='label')


# #### Merge features
# Create subset of features to be merged
min_area = 50
seg[merge] = seg.geometry.area < min_area
subset = seg[seg[merge]==True]

x = get_neighbors(seg, subset=subset, unique_id=unique_id)
for index, row in x.iterrows():
    if row[merge] == True:
        




# ns = []
# labels = []
# for index, row in seg.iterrows():  
#     if row['diff_mean'] < diff_thres:
#         neighbors = seg[seg.geometry.touches(row['geometry'])]['label'].tolist() 
#         if row['label'] in neighbors:
#             neighbors = neighbors.remove(row['label'])
#     else:
#         neighbors = None
    
#     ns.append(neighbors)
#     labels.append(row['label'])
        
    # seg.at[index, "neighbors"] = neighbors
    # print(index)
    
# nebs = pd.DataFrame({'label':labels, 'neighbors':ns})
# result = pd.merge(seg,
#                   nebs,
#                   how='left',
#                   on='label')



# tks = seg[seg['diff_mean'] < diff_thres]
# tks.to_file(r'V:\\pgc\\data\\scratch\\jeff\\ms\\scratch\\aoi6_good\\seg\\WV02_20150906_clip_ms_lsms_sr5rr200ss150_tks.shp')