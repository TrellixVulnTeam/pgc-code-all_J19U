# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 18:10:03 2020

@author: disbr007
"""
import IPython
# IPython.start_ipython() 

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
    # if row.name in neighbors:
        # neighbors = neighbors.remove(row.index)
    
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


def closest_neighbor(row, vc, nvc, vt, ignore_ids):
    """
    Find closest neighbor value given dict of neighbor ids:values
    and value to compare to. Also check that value isn't in list
    ids to ignore.
    
    Parameters
    ----------
    row : gpd.GeoSeries (?)
        Row to determine if adjacent to feature value passed.
    vc : str
        Column in row containing value to find closest to.
    vt : int, float
        How far away a neighbor value will be included. ("value threshold")
        If farther than this threshold, neighbor is skipped.
    nvc : str
        Column containing dictionary of neighbor_id: value.
    ignore_ids : list
        List of IDs to exclude from choosing.
        
    Returns
    ---------
    str : ID of closest neighbor
    """
    
    # Get the value of the feature
    feat_val = row[vc]
    
    # Remove any ignore_ids from the dictionary
    neighbor_vals = row[nvc]
    # Check if neighbor values nan ******
    # if pd.isnull(neighbor_vals):
        # logger.debug(row)
    # logger.info('\n')
    # logger.info('\n{}'.format(row))
    
    for key in list(neighbor_vals.keys()):
        if key in ignore_ids:
            neighbor_vals.pop(key, None)
    
    # Remove any ids if their values further than threshold
    neighbor_vals = {k: v for k, v in neighbor_vals.items() if abs(v-feat_val) <= vt}
    
    # Check to ensure values remain in dictionary
    if neighbor_vals:
        # Get the id of the closest value in the dictionary
        id_closest = min(row[nvc].items(), key=lambda kv : abs(kv[1] - feat_val))[0]
    else:
        id_closest = None
        
    return id_closest

    
def merge(gdf, to_merge, col_of_int):
    """
    Create geodataframe from list of IDs in list of tuples (id, dissolve_ct). Dissolve that geodataframe
    on the dissolve ct. Remove those IDs from gdf. Recombine dissolved features with gdf.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Master geodataframe containing all IDs in to_merge.
    to_merge : dict
        dict of ID:dissolve_ct to look up in gdf, dissolve and recombine.
    col_of_int : str
        Column to aggregate
        
    Returns
    -------
    gpd.GeoDataFrame : Merged geodataframe.

    """
    # Create df of subset
    dis_feats = gdf[gdf.index.isin(to_merge.keys())]
    
    # Get the dissolve identifiers
    index_name = dis_feats.index.name
    if not index_name:
        index_name = 'temp_index'
    dis_feats.index.name = index_name
    dis_feats.reset_index(inplace=True)
    dis_feats['dis'] = dis_feats[index_name].apply(lambda x: to_merge[x])
    dis_feats.set_index(index_name, inplace=True)
    
    ## Dissolve subset (agg funct area weighted)
    # Create value*area column for creating area weighted column (at: area total)
    dis_feats['at_{}'.format(col_of_int)] = dis_feats[col_of_int] * dis_feats.geometry.area
    # Dissolve
    dis_feats = dis_feats.dissolve(by='dis', aggfunc = 'sum')
    # Divide area total columns by area to get area weighted values
    dis_feats['aw_{}'.format(col_of_int)] = dis_feats['at_{}'.format(col_of_int)] / dis_feats.geometry.area
    
    # Just keep area weighted column (and geometry)
    dis_feats = dis_feats[['aw_{}'.format(col_of_int), 'geometry']]
     
    # Rename the column back to original name
    rename = {'aw_{}'.format(col_of_int): col_of_int}
    dis_feats.rename(columns=rename, inplace=True)
    # Create new index values to ensure no duplicates
    max_unique_id = gdf.index.max()
    new_idx = [max_unique_id+1+ i for i in range(len(dis_feats))]
    dis_feats.set_index([new_idx], inplace=True)
    
    # Remove ids that are in to_merge from gdf
    gdf = gdf[~gdf.index.isin(to_merge.keys())]
    
    # Add back to gdf
    gdf = pd.concat([gdf, dis_feats])
    
    # logger.info('Merge success')
    
    return gdf


unique_id = 'label'
gdf = gpd.read_file(r'C:\temp\merge_test.shp')
import copy
g = copy.deepcopy(gdf)
gdf = gdf[[unique_id, 'tpi31_mean', 'slope_mean', 'geometry']]

gdf.set_index(unique_id, inplace=True)
logger.debug('DataFrame has unique index: {}'.format(str(gdf.index.is_unique)))

tpi31_mean = 'tpi31_mean'
neighbor_col = 'nebs'
nv_tpi31 = 'nv_tpi31'
adj_tpi_col = 'adj_tpi31_neg1x5'
adj_tpi31_thesh = -1.5

gdf[nv_tpi31] = gdf.apply(lambda x: neighbor_values(x, gdf, tpi31_mean, nc=None), axis=1)

# gdf = gdf.head(12)
# to_merge = {21166:1, 21625:1, 20976:2, 21344:2}
# x = merge(gdf, to_merge, 'tpi31_mean')

# params
vc = tpi31_mean
nvc = nv_tpi31        
vt = 5
iter_btw_merge = 15

# import copy
# g = copy.deepcopy(gdf)
# sub_ids = g.iloc[0:5, :].index.tolist()
# g.loc[g.index.isin(sub_ids), nvc] = g.apply(lambda x: neighbor_values(x, g, vc=vc), axis=1)


# Flag for when there are no remaining features to merge
fts_to_merge = True
# IDs with no matches
skip_ids = []
unique_idx = gdf.index.is_unique
while unique_idx:
    while fts_to_merge:
        # Dict to store ID: dissolve_value
        to_merge = {}
        # Dissolve value counter, increased everytime a match is found
        dissolve_ctr = 0
        
        # Create subset (min_size > s)
        subset = gdf[(gdf.geometry.area < 900) & (~gdf.index.isin(skip_ids))] # fix to be a function
        if len(subset) <= 0:
            fts_to_merge = False
            break
        
        unique_idx = gdf.index.is_unique
        if not unique_idx:
            logger.info('1')
            fts_to_merge = False
        
        # Check if any nans in nvc in subset (newly merged) -> recomp neighbor values for those 
        if any(pd.isnull(subset[nvc])):
            # gdf[gdf.index.isin(subset.index)][]
            # gdf[gdf.index.isin(subset.index)][nvc] = gdf[gdf.index.isin(subset.index)].apply(lambda x: neighbor_values(x, gdf, vc), axis=1)
            
            # get ids of with null nvc column
            null_ids = subset[pd.isnull(subset[nvc])].index.tolist()
            # get neighbor values
            # gdf.loc[gdf.index.isin(null_ids), nvc] = gdf.apply(lambda x: neighbor_values(x, gdf, vc=vc), axis=1)
            gdf[gdf.index.isin(null_ids)][nvc] = gdf.apply(lambda x: neighbor_values(x, gdf, vc=vc), axis=1)
            # recreate subset
            subset = gdf[(gdf.geometry.area < 900) & (~gdf.index.isin(skip_ids))] # fix to be a function
            
            unique_idx = gdf.index.is_unique
            if not unique_idx:
                logger.info('2')
                fts_to_merge = False
        
        
        # Iterate rows
        for i, row in subset.iterrows():
            # Find closest neighbor
            # Add row id and closest neighbor to to_merge seperately with same dissolve counter
            match = closest_neighbor(row, vc, 
                                      nvc=nvc, 
                                      vt=vt,
                                      ignore_ids=to_merge.keys())
            if match:
                # Add index of current row and its match with same dissolve value
                to_merge[row.name] = dissolve_ctr
                to_merge[match] = dissolve_ctr
                dissolve_ctr += 1
            else:
                # if no match found exclude from further checks
                skip_ids.append(row.name)
            
            # If number of features before merge, merge, exit loop, start loop over with new gdf
            if len(to_merge) >= iter_btw_merge:
                logger.info('*****MERGE******')
                # import sys
                # sys.exit()
                gdf = merge(gdf, to_merge, col_of_int=vc)
                
                unique_idx = gdf.index.is_unique
                if not unique_idx:
                    logger.info('3.1')
                    fts_to_merge = False
                # to_merge = {} # empty dist of to ids to merge
                
                # start geodataframe iteration over with merged geodataframe
                break
            
            # End of the loop over subset is reached before the iter_btw_merge threshold
            gdf = merge(gdf, to_merge, col_of_int=vc)
            unique_idx = gdf.index.is_unique
            if not unique_idx:
                logger.info('3')
                fts_to_merge = False


# Iterate over sorted gdf
    # Find closest neighbor
    # Add to new df or list of ids, with counter
    # Mark both as ignore=True
    # Add one to counter
    # If no match possible, add to list of ids to ignore

# Remove all ids in new df from original df
# Dissolve 
# Add dissolved features back in
            
import matplotlib.pyplot as plt

plt.style.use('ggplot')
fig, ax = plt.subplots(1,1)

gdf.plot(ax=ax, column='tpi31_mean', edgecolor='white', linewidth=2.5)
g.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.45, legend=True)
# # gdf.plot(column='tpi31_mean', ax=ax, edgecolor='white', linewidth=0.25, legend=True)
# # gdf.plot(column=adj_tpi_col, ax=ax, edgecolor='black', linewidth=0.25, legend=True)

ax.axis('off')