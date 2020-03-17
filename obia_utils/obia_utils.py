# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 12:27:22 2020

@author: disbr007
"""

import os
import logging.config
from tqdm import tqdm

import pandas as pd

from misc_utils.logging_utils import LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(os.path.basename(__file__).split('.')[0])


def get_value(df, lookup_field, lookup_value, value_field):
    val = df[df[lookup_field]==lookup_value][value_field]
    if len(val) == 0:
        logger.error('Lookup value not found: {} in {}'.format(lookup_value, lookup_field))
    elif len(val) > 1:
        logger.error('Lookup value occurs more than once: {} in {}'.format(lookup_value, lookup_field))
    
    return val.values[0]


def get_neighbors(gdf, subset=None, unique_id=None, neighbor_field='neighbors'):
    """
    Gets the neighbors for a geodataframe with polygon geometry
    geodataframe, optionally only a subset.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to compute neighbors in, must be polygon/multipolygon.
    subset : gpd.GeoDataFrame
        Selected rows from gdf to compute neighbors for. Highly recommended 
        for large dataframes as neighbor computation can be slow.
    unique_id : str
        Unique field name in gdf and subset to use as identifier. The default is None.
    neighbor_field : str
        The name of the field to create to store neighbor unique_ids.

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
        neighbors = gdf[gdf.geometry.touches(row['geometry'])][unique_id].tolist()
        # If the feature is considering itself a neighbor remove it from the list
        # TODO: clean this logic up (or just the comment) 
        #       when does a feature find itself as a neighbor?
        if row[unique_id] in neighbors:
            neighbors = neighbors.remove(row[unique_id])
        
        # Save the neighbors that have been found and their IDs
        ns.append(neighbors)
        labels.append(row[unique_id])

    # Create data frame of the unique ids and their neighbors
    nebs = pd.DataFrame({unique_id:labels, neighbor_field:ns})
    # Combine the neighbors dataframe back into the main dataframe, joining on unique_id
    # essentially just adding the neighbors column
    result = pd.merge(gdf,
                      nebs,
                      how='left',
                      on=unique_id)
    logger.info('Neighbor computation complete.')
    
    return result


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
    # For each neighbor id in the list of neighbor ids, create an entry in 
    # a dictionary that is the id and its value.
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
    gdf : gpd.GeoDataFrame (or pd.DataFrame)
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
    result : gpd.GeoDataFrame (or pd.Dataframe)
        DataFrame with added field [adjacent_field], which is a boolean series indicating
        whether the feature meets requirements of having a neighbor that meets the value
        threshold indicated.

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
        if value_compare == '<':
            ## Assuming value compare operator is less than for testing
            matches = [v < value_thresh for k, v in values.items()]
        elif value_compare == '>':
            matches = [v < value_thresh for k, v in values.items()]
        elif value_compare == '==':
            matches = [v == value_thresh for k, v in values.items()]
        elif value_compare == '!=':
            matches = [v != value_thresh for k, v in values.items()]
        else:
            logger.error("""value_compare operater not recognized, must be
                            one of: ['<', '>', '==', '!='. 
                            value_compare: {}""".format(value_compare))
        if any(matches):
            have_adj.append(row[unique_id])
    
    # If feature had neighbor meeting threshold, return True, else False
    gdf[adjacent_field] = gdf[unique_id].isin(have_adj)
    
    return gdf