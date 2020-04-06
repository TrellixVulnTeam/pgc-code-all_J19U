# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 18:10:03 2020

@author: disbr007
"""

import operator

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger

pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh' ,'DEBUG')


def get_truth(inp, relate, cut):
    """
    Evaluates a statement: inp compared to cut based on relate.
    
    Parameters
    ----------
    inp : object
        value on the left of the comparison (e.g.: inp < x)
    relate : str
        comparison operator to use. one of 
        ['>', '<', '>=', '<=', '==', '!=']
    cut : object
        value on the left of the comparison (e.g. x > cut)
    
    Returns
    --------
    bool : True if statement is True.
    """
    ops = {'>': operator.gt,
           '<': operator.lt,
           '>=': operator.ge,
           '<=': operator.le,
           '==': operator.eq}
     
    return ops[relate](inp, cut)


def find_neighbors(row, gdf):
    """
    Gets neighbor indicies for the given row in the given geodataframe.
    Requires index of gdf is unique.

    Parameters
    ----------
    row : TYPE
        DESCRIPTION.
    gdf : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    if not gdf.index.is_unique:
        logger.warning("""Index of GeoDataFrame to compute neighbors on
                          is not unique.""")
    # Get the indicies of features in gdf that touch the row's geometry
    neighbors = gdf[gdf.geometry.touches(row.geometry)].index.tolist()
    # Check if current feature was included as one of it's own neighbors
    if row.name in neighbors:
        neighbors = neighbors.remove(row.index)
    
    return neighbors


def neighbor_values(row, gdf, vc, nc=None):
    """
    Gets values in the given column of neighbors (which can either) be
    computed already or not.
    
    Parameters
    ----------
    row : gpd.GeoSeries (?)
        Row to find neighbor values for
    gdf : gpd.GeoDataFrame
        GeoDataFrame to look values up in, must contain all neighbors.
    vc : str
        Name of column to look up value in. (vc: "Value column")
    nc : str
        Name of column containing list of neighbor indicies. Default = None.
    
    Returns
    ---------
    list of tuple : [(neighbor index, value), (n_2, v_2), ... (n_i, v_i)]
        The index of each neighbor and its value.
    """
    # Neighbors list
    if not nc:
        neighbors = find_neighbors(row, gdf)
    else:
        neighbors = row[nc]
    # Get value for each neighbor
    values = {n: gdf.loc[n, vc] for n in neighbors}

    return values
    
    
def adj_neighbor(row, vt, nvc, tc):
    """
    Determine if the row is adjacent to a feature based on the comparison
    method passed.

    Parameters
    ----------
    row : gpd.GeoSeries (?)
        Row to determine if adjacent to feature value passed.
    vt : int, float, str
        The value to compare value column to. ("value threshold")
    nvc : str
        Column containing dictionary of neighbor_id: value.
    tc : str
        The comparison operator to use: [">", "<", "!=', "==", ">=", "<="]


    Returns
    -------
    Bool : True if row adjacent to feature meating passed requirements.

    """
    values = row[nvc]
    
    match = any([get_truth(v, tc, vt) for v in values.values()])
    
    return match


def closest_neighbor(row, nvc, vc, ignore_col):
    """
    Determine which neighbor has the value closest to the row's value in
    the passed column.
    
    Parameters
    ----------
    row : gpd.GeoSeries (?)
        Row to determine if adjacent to feature value passed.
    vt : int, float, str
        The value to compare value column to. ("value threshold")
    nvc : str
        Column containing dictionary of neighbor_id: value.
    ignore_col : str
        name of column containing BOOL - True to skip that feature
        
    Returns
    ---------
    str : ID of closest neighbor
    """
    # Find closest neighbor value given dict of neighbor ids:values
    # and value to compare to. Also consider a bool ignore_col.
    pass

# Iterate over sorted gdf
    # Find closest neighbor
    # Add to new df or list of ids, with counter
    # Mark both as ignore=True
    # Add one to counter

# Remove all ids in new df from original df
# Dissolve 
# Add dissolved features back in
    

unique_id = 'label'
gdf = gpd.read_file(r'C:\temp\merge_test.shp')
gdf = gdf[[unique_id, 'tpi31_mean', 'slope_mean', 'geometry']]
gdf.set_index(unique_id, inplace=True)
logger.debug('DataFrame has unique index: {}'.format(str(gdf.index.is_unique)))

neighbor_col = 'nebs'
nv_tpi31 = 'nv_tpi31'
adj_tpi_col = 'adj_tpi31_neg1x5'
adj_tpi31_thesh = -1.5

# gdf[neighbor_col] = gdf.apply(lambda x: get_neighbors(x, gdf), axis=1)
gdf[nv_tpi31] = gdf.apply(lambda x: neighbor_values(x, gdf, 'tpi31_mean', nc=None), axis=1)

gdf[adj_tpi_col] = gdf.apply(lambda x: adj_neighbor(x, adj_tpi31_thesh, nv_tpi31, '<'), axis=1)


import matplotlib.pyplot as plt

plt.style.use('ggplot')
fig, ax = plt.subplots(1,1)
# gdf.plot(column='tpi31_mean', ax=ax, edgecolor='white', linewidth=0.25, legend=True)
gdf.plot(column=adj_tpi_col, ax=ax, edgecolor='black', linewidth=0.25, legend=True)
ax.axis('off')