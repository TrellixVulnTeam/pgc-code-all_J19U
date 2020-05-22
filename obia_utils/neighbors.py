# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 18:10:03 2020

@author: disbr007
"""
# import IPython
# IPython.start_ipython() 

import operator

import pandas as pd
from pandas.api.types import is_numeric_dtype
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
           '==': operator.eq,
           '!=': operator.ne}

    return ops[relate](inp, cut)


def subset_df(gdf, params, skip_ids=None):
    """
    Return a subset of the given dataframe, which is nrows long after sorting by col in order
    provided.

    Parameters
    ----------
    gdf : pd.DataFrame
        DataFrame to create subset from.
    params : list
        list of tuples of (column name, compare operator, threshold). E.g. ('slope_mean', '<', 10)
    skip_ids : list
        List of index values in gdf to exclude in even if they meet params
    Returns
    -------
    pd.DataFrame or gpd.GeoDataFrame.

    """
    # TODO: Add checking to enure params is formated properly:
    #       [(column_name, compare, thresh), (col2, comp2, thresh2), ...]
    #       [('slope_mean', '<', 10)]
    # Check operators are correct
    invalid_params = [p for p in params if p[1] not in ['<', '>', '<=', '>=', '==', '!=']]
    if any(invalid_params):
        logger.error('Invalid operator(s) supplied in params: {}'.format(invalid_params))

    param_str = '\n'.join([str(p).replace("'", "").replace(",", "").replace("(", "").replace(")", "") for p in params])
    logger.debug('Subsetting where:\n{}'.format(param_str))

    # Check if "area" is any of the columns to use
    # If it is, and is not already a column, create it
    if "area" in [p[0] for p in params] and "area" not in gdf.columns:
        gdf["area"] = gdf.geometry.area

    # Do initial subset with first params
    subset = gdf[get_truth(gdf[params[0][0]], params[0][1], params[0][2])]
    if len(params) > 1:
        for p in params[1:]:
            subset = subset[get_truth(subset[p[0]], p[1], p[2])]

    if len(subset) == 0:
        logger.debug('Empty subset returned:\n{}'.format(param_str))

    if skip_ids:
        subset = subset[~subset.index.isin(skip_ids)]
    logger.debug('Subset size: {}'.format(len(subset)))
    
    return subset


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
    Get values in the given column of neighbors (which can either) be
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

    Returnsnie
    ---------
    list of tuple : [(neighbor index, value), (n_2, v_2), ... (n_i, v_i)]
        The index of each neighbor and its value.
    """
    # Neighbors list
    if not nc:
        neighbors = find_neighbors(row, gdf)
    else:
        neighbors = row[nc]
    # Get value for each neighbor, skip neighbors with nan value in vc column
    values = {n: gdf.loc[n, vc] for n in neighbors
              if not pd.isnull(gdf.loc[n, vc])}

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
    Bool : True if row adjacent to a feature meating passed requirements.

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
        dict of ID:dissolve_ct to look up in gdf, dissolve, and recombine.
    col_of_int : str
        Column to aggregate

    Returns
    -------
    gpd.GeoDataFrame : Merged geodataframe.

    """
    # Create df of subset
    dis_feats = gdf[gdf.index.isin(to_merge.keys())]

    # Get the dissolve identifiers

    index_name = gdf.index.name
    if not index_name:
        index_name = 'temp_index'
    dis_feats.index.name = index_name
    dis_feats.reset_index(inplace=True)

    dis_feats['dis'] = dis_feats[index_name].apply(lambda x: to_merge[x])

    # dis_feats.set_index(index_name, inplace=True)

    ## Dissolve subset (agg funct area weighted)
    # Create value*area column for creating area weighted column (at: area total)
    dis_feats['at_{}'.format(col_of_int)] = dis_feats[col_of_int] * dis_feats.geometry.area
    # Dissolve
    cols = dis_feats.columns.tolist()
    cols = [c for c in cols if is_numeric_dtype(dis_feats[c])]
    # cols.remove('geometry')
    # cols.remove('')
    agg = {col:'sum' for col in cols}
    agg[index_name] = 'first'
    dis_feats = dis_feats.dissolve(by='dis', aggfunc = agg)
    dis_feats.set_index(index_name, inplace=True)

    # Divide area total columns by area to get area weighted values
    dis_feats['aw_{}'.format(col_of_int)] = dis_feats['at_{}'.format(col_of_int)] / dis_feats.geometry.area
    dis_feats.index.name = index_name
    # Just keep area weighted column (and geometry)
    dis_feats = dis_feats[['aw_{}'.format(col_of_int), 'geometry']]

    # Rename the column back to original name
    rename = {'aw_{}'.format(col_of_int): col_of_int}
    dis_feats.rename(columns=rename, inplace=True)
    # Create new index values to ensure no duplicates
    # max_unique_id = gdf.index.max()
    # new_idx = [max_unique_id+1+ i for i in range(len(dis_feats))]
    # dis_feats.set_index([new_idx], inplace=True)

    # Remove ids that are in to_merge from gdf
    gdf = gdf[~gdf.index.isin(to_merge.keys())]

    # Add back to gdf
    gdf = pd.concat([gdf, dis_feats])

    # logger.info('Merge success')

    return gdf


def split_nan_features(gdf, vc):
    #
    # Remove any features with nan in their vc (value column)
    nan_feats = None
    if any(pd.isnull(gdf[vc])):
        logger.warning('Removing features with NaN values in column to merge on: {}'.format(vc))
        nan_feats = gdf[pd.isnull(gdf[vc])]
        gdf = gdf[~pd.isnull(gdf[vc])]

    return gdf, nan_feats


def merge_closest_val(gdf, vc, vt, nvc, subset_params, iter_btw_merge=100):
    """
    Write a good docstring
    later.
    """
    logger.info('Starting number of features: {:,}'.format(len(gdf)))
    # TODO: Check for unique index and index.name
    # TODO: Non-consistent results with different iter_btw_merge
    # TODO: Warn if nvc not computed

    # Temporarily remove any features with nan in the column of interest
    gdf, nan_feats = split_nan_features(gdf, vc=vc)

    # Check if neighbor value column exists
    if not nvc in gdf.columns:
        gdf[nvc] = None
        logger.debug('Neighbors not previously located.')
        # # Create subset of features that meet subset parameters [(column, compare, thresh),...]
        # subset = subset_df(gdf, params=subset_params)
        # # Get neighbors for those features that meet subset parameters
        # gdf[nvc] = gdf[gdf.index.isin(subset.index)].apply(lambda x: neighbor_values(x, gdf, vc=vc), axis=1)

    # Flag for when there are no remaining features to merge
    fts_to_merge = True

    # Store IDs with no matches
    skip_ids = []

    while fts_to_merge:
        # Dict to store ID: dissolve_value
        to_merge = {}
        # Dissolve value counter, increased everytime a match is found
        dissolve_ctr = 0

        # Create subset of features that meet subset parameters [(column, compare, thresh),...]
        subset = subset_df(gdf, params=subset_params, skip_ids=skip_ids)
        if len(subset) <= 0:
            fts_to_merge = False
            break

        # Check if any nans in nvc in subset (newly merged) -> recomp neighbor values for those
        if any(pd.isnull(subset[nvc])):
            # Get ids of with null nvc column
            null_ids = subset[pd.isnull(subset[nvc])].index.tolist()

            # Get missing neighbor-values
            idx_name = gdf.index.name
            missing_neighbors = gdf[gdf.index.isin(null_ids)].apply(lambda x: neighbor_values(x, gdf, vc=vc), axis=1)
            # Set created series name to match neighbor value column name in gdf
            missing_neighbors.name = nvc
            # Set created series index name to match index name in gdf
            missing_neighbors.index.name = idx_name  
            # Replace the values in neighbor value column with any newly calculated neighbor values
            gdf.update(missing_neighbors)

            # Recreate subset
            subset = subset_df(gdf, params=subset_params, skip_ids=skip_ids)
            # subset = gdf[(gdf.geometry.area < 900) & (~gdf.index.isin(skip_ids))]  # Fix to be a function

        # Iterate rows of subset
        for i, row in subset.iterrows():
            # Find closest neighbor
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
                # If no match found exclude ID from further checks
                skip_ids.append(row.name)

            # If number of features before merge, merge, exit loop, start loop over with new gdf
            if len(to_merge) >= iter_btw_merge:
                logger.debug('Merging features: {:,}...'.format(len(to_merge)))
                gdf = merge(gdf, to_merge, col_of_int=vc)

                # start geodataframe iteration over with merged geodataframe
                break

        # End of the loop over subset is reached before the iter_btw_merge threshold
        logger.debug('End of subset, merging features: {:,}'.format(len(to_merge)))
        gdf = merge(gdf, to_merge, col_of_int=vc)

    # Add back in any features that had NaN in the vc.
    if isinstance(nan_feats, gpd.GeoDataFrame):
        gdf = pd.concat([gdf, nan_feats])

    logger.info('Resulting number of features: {:,}'.format(len(gdf)))
    
    return gdf
