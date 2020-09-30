# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 12:27:22 2020

@author: disbr007
"""
# import traceback, sys, pdb
import copy
from random import randint
from tqdm import tqdm

import numpy as np
from osgeo import ogr, gdal
import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger #LOGGING_CONFIG
from misc_utils.RasterWrapper import Raster
# from obia_utils.calc_zonal_stats import calc_zonal_stats
# from calc_zonal_stats import calc_zonal_stats

gdal.UseExceptions()

logger = create_logger(__name__, 'sh', 'INFO')


def get_value(df, lookup_field, lookup_value, value_field):
    val = df[df[lookup_field] == lookup_value][value_field]
    if len(val) == 0:
        logger.error('Lookup value not found: {} in {}'.format(lookup_value, lookup_field))
    elif len(val) > 1:
        logger.error('Lookup value occurs more than once: {} in {}'.format(lookup_value, lookup_field))
    
    return val.values[0]


def get_neighbors(gdf, subset=None, unique_id=None, neighbor_field='neighbors'):
    """
    Adds column with the IDs of neighbors for a geodataframe with polygon geometry
    geodataframe, optionally only a subset of that geodataframe.

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
    # TODO: Turn this into an apply function that takes the row and
    #       returns the neighbors
    # If no subset is provided, use the whole dataframe
    if subset is None:
        subset = gdf

    # List to store neighbors
    ns = []
    # List to store unique_ids
    labels = []
    # Iterate over rows, for each row, get unique_ids of all features it touches
    print('Getting neighbors for {} features...'.format(len(subset)))
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

    if not any(ns):
        logger.warning('No neighbors found.')
    # Create data frame of the unique ids and their neighbors
    nebs = pd.DataFrame({unique_id: labels, neighbor_field: ns})
    # Combine the neighbors dataframe back into the main dataframe, joining on unique_id
    # essentially just adding the neighbors column
    gdf[unique_id] = gdf[unique_id].astype(str)
    nebs[unique_id] = nebs[unique_id].astype(str)

    # gdf_cols = list(gdf.columns)
    # if neighbor_field not in gdf.columns:
    #     gdf[neighbor_field] = [[] for i in range(len(gdf))]
    #     gdf_cols.append(neighbor_field)

    result = pd.merge(nebs,
                      gdf,
                      how='left',
                      suffixes=('', '_y'),
                      on=unique_id)
    # result = result[gdf_cols]
    print('Neighbor computation complete.')

    return result


def neighbor_features(unique_id, gdf, subset=None, neighbor_ids_col='neighbors'):
    """
    Create a new geodataframe of neighbors for all features in subset. Finds neighbors if
    neighbor_ids_col does not exist already.

    Parameters
    ----------
    unique_id : str
        Column containing unique ids for each feature.
    gdf : gpd.GeoDataFrame
        Full geodataframe containing all features.
    subset : gpd.GeoData, optional
        Subset of gdf containing only features to find neighbors for. The default is None.
    neighbor_ids_col : str, optional
        Column in subset (and gdf) containing neigbor unique IDs. If column doesn't exist,
        the column name in which to put neighbor IDs, The default is None.

    Returns
    -------
    neighbor_feats : gpd.GeoDataFrame
        GeoDataFrame containing one row per neighbor for each row in subset. Will contain
        repeated geometries if features in subset share neighbors.

    """
    # Compute for entire dataframe if subset is not provided.
    if not isinstance(subset, (gpd.GeoDataFrame, pd.DataFrame)):
        subset = gdf

    # Find neighbors if column containing neighbor IDs does not already exist
    if not neighbor_ids_col in subset.columns:
        subset = get_neighbors(gdf=gdf, subset=subset, unique_id=unique_id,
                               neighbor_field=neighbor_ids_col)

    # Store source IDs and neighbor IDs in lists
    source_ids = []
    neighbor_ids = []
    for i, row in subset.iterrows():
        # Get all neighbors of current feature, as list, add to master list
        neighbors = row[neighbor_ids_col]
        neighbor_ids.extend(neighbors)
        # Add source ID to list one time for each of its neighbors
        for n in neighbors:
            source_ids.append(row[unique_id])
    # Create 'look up' dataframe of source IDs and neighbor ids
    src_lut = pd.DataFrame({'neighbor_src': source_ids, 'neighbor_id': neighbor_ids})

    # Find each neighbor feature in the master GeoDataFrame, creating a new GeoDataFrame
    neighbor_feats = gpd.GeoDataFrame()
    for ni in neighbor_ids:
        feat = gdf[gdf[unique_id] == ni]
        neighbor_feats = pd.concat([neighbor_feats, feat])

    # Join neighbor features to sources
    # This is one-to-many with one row for each neighbor-source pair
    neighbor_feats = pd.merge(neighbor_feats, src_lut, left_on=unique_id, right_on='neighbor_id')
    # Remove redundant neighbor_id column - this is the same as the unique_id in this df
    neighbor_feats.drop(columns=['neighbor_id'], inplace=True)

    return neighbor_feats


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
    try:
        # For each neighbor id in the list of neighbor ids, create an entry in 
        # a dictionary that is the id and its value.
        values = {}
        for n in neighbors:
            match = df[df[unique_id] == n][value_field].values
            if len(match) == 1:
                values[n] = match
            else:
                values[n] = np.NaN
        print(neighbors)
        logger.info(neighbors)
        # values = {n: df[df[unique_id] == n][value_field].values[0] for n in neighbors}
    except Exception as e:
        print(neighbors)
        print(e)
        # extype, value, tb = sys.exc_info()
        # traceback.print_exc()
        # pdb.post_mortem(tb)
        raise Exception
        
    
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
    if neighbor_field not in gdf.columns:
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
            matches = [v > value_thresh for k, v in values.items()]
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


def mask_class(gdf, column, raster, out_path, mask_value=1):
    """
    Mask (set to NoData) areas of raster where column == mask_value in gdf.
    Designed to mask an already classified area from subsequent 
    segmentations/classifications, or to mask everything except class-candidate 
    areas for resegmentation.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame containing column and polygon geometries to be masked.
    column : str
        Name of column containing values to burn into raster.
    raster : str
        TODO: Make this an already open raster object
        Path to raster to be masked.
    out_path : str
        Path to masked raster. This can be an in-memory location ('/vsimem/temp.tif').
    mask_value : int, float, str, optional
        The value of column, where corresponding geometries should be set to NoData
        in output raster. The default is 1.

    Returns
    -------
    out_path : str

    """
    # Random number to append to temporary filenames to *attempt* to avoid overwriting if
    # multiprocessing
    ri = randint(0, 1000)

    # Save class to temporary vector file
    temp_seg = r'/vsimem/temp_seg_class{}.shp'.format(ri)
    gdf[[column, 'geometry']].to_file(temp_seg)
    vect_ds = ogr.Open(temp_seg)
    vect_lyr = vect_ds.GetLayer()
    
    # Get metadata from raster to be burned into
    img = Raster(raster)
    ulx, uly, lrx, lry = img.get_projwin()
    
    # Create output datasource with same metadata as input raster
    temp_rast = r'/vsimem/temp_seg_rast{}.vrt'.format(ri)
    target_ds = gdal.GetDriverByName('GTiff').Create(temp_rast, img.x_sz, img.y_sz, 1, img.dtype)
    target_ds.SetGeoTransform(img.geotransform)
    target_band = target_ds.GetRasterBand(1)
    target_band.SetNoDataValue(img.nodata_val)
    target_band.FlushCache()
    
    # Rasterize attribute into output datasource
    gdal.RasterizeLayer(target_ds, [1], vect_lyr, options=["ATTRIBUTE={}".format(column)])
    
    # Read rasterized layer as array
    t_arr = target_ds.ReadAsArray()
    target_ds = None
    
    # Get original image as array
    o_arr = img.MaskedArray
    
    # Convert where the column is value to no data in the orginal image, keeping other original
    # values
    new = np.where(t_arr == mask_value, img.nodata_val, o_arr)
    
    # Write the updated array/image out
    img.WriteArray(new, out_path)
        
    return out_path


def merge(gdf, unique_id, neighbor_field, feat,
          merge_col, merge_thresh,):
    """
    Merge features in gdf that meet subset criteria. Removes the original features
    and replaces them with the merged features.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame of features to merge.
    subset_col : str
        Name of column to use to create subset to merge in.
    subset_thresh : int / float / str
        Value subset column must meet to be included.
    subset_compare : str
        Comparison operator for subset_col vs subset_thresh.

    Returns
    -------
    gpd.GeoDataFrame : gdf but with merged features.

    """
    
    # if neighbor_field not in subset.columns:
    #     subset = get_neighbors(gdf, subset=subset, unique_id=unique_id,
    #                             neighbor_field=neighbor_field)
    
    feat_id = feat[unique_id].values[0]
    feat_val = feat[merge_col].values[0]
    values = neighbor_values(feat, unique_id, feat[neighbor_field], merge_col)
    merge_candidates = {fid: val for fid, val in values.items()
                        if feat_val-merge_thresh <= val <= feat_val+merge_thresh}
    if len(merge_candidates) == 0:
        logger.warning('No merge candidate found. Returning original feature')
        return gdf

    # Find best matching neighbor, closest merge_col value
    absolute_difference_function = lambda list_value : abs(list_value - feat_val)
    closest_val = min(merge_candidates.values(), key=absolute_difference_function)
    merge_id = [fid for fid, val in merge_candidates.items()
                if val == closest_val]
    
    # Create geodataframe of just feature and neighbor to merge with
    # Get geodataframe of just ids to merge
    merge_id.append(feat_id)
    to_merge = copy.deepcopy(gdf[gdf[unique_id].isin(merge_id)])
    
    # Merge
    # Dummy field to merge on
    to_merge.loc[:, 'merge_temp'] = 1
    merged = to_merge.dissolve(by='merge_temp')
    # Create new unique id
    merged[unique_id] = gdf[unique_id].max()+1
    
    # Remove original feat and neighbor merged with from master
    gdf = gdf[~gdf[unique_id].isin(merge_id)]
    
    # Add merged to master
    gdf = pd.concat([gdf, merged])
    
    return gdf


def create_subset(gdf, subset_col, subset_thresh, subset_compare):
    # TODO: Change this to use operator module
    # Create subset
    if subset_compare == '<':
        subset = gdf[gdf[subset_col] < subset_thresh]
    elif subset_compare == '>':
        subset = gdf[gdf[subset_col] > subset_thresh]
    elif subset_compare == '==':
        subset = gdf[gdf[subset_col] == subset_thresh]
    elif subset_compare == '!=':
        subset = gdf[gdf[subset_col] != subset_thresh]
    else:
        logger.info('Unrecognized comparison operator: {}'.format(subset_compare))
    
    return subset


# Merge similar
# Load data
# seg = gpd.read_file(r'C:\temp\merge_test.shp')
# # seg = pd.read_pickle(r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_tpi31_tpi81_tpi101_stk_a6g_sr5_rr0x35_ms100_tx500_ty500_stats_nbs.pkl')

# subset = copy.deepcopy(seg)

# Created fields
# unique_id = 'label'
# neighbor_fld = 'neighb'
# skip_merge = 'skip_merge'

# seg = get_neighbors(seg, subset=subset, unique_id=unique_id, neighbor_field=neighbor_fld)
# # seg.to_pickle(r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_tpi31_tpi81_tpi101_stk_a6g_sr5_rr0x35_ms100_tx500_ty500_stats_nbs.pkl')

# subset_col = 'area_zs'
# subset_thresh = 500
# subset_compare = '<'

# merge_col = 'slope_mean' # column to use to find neighbor to merge with
# merge_thresh = 1.5 # threshold merge_col must be within to merge

# merge_stop_col = 'area_zs' # or something else
# merge_stop_val = 500 # minimum size for example
# merge_stop_compare = '<'
# # if you need to recalc stats while merging (e.g. to calc new 'slope_mean'), 
# # not need for area calc for example
# # if using built in geopandas area attribute
# recalc_int = False

# # Sort gdf by sort criteria
# sort_col = 'area_zs' # column to sort by before starting merge process
# seg.sort_values(by=sort_col, inplace=True)


# # testing -- save orignal features to be merged
# should_merge = create_subset(gdf=seg, subset_col=subset_col, 
#                              subset_thresh=subset_thresh, 
#                              subset_compare=subset_compare)

# # Check if any features in the master need to be merged
# # merging = any(seg[merge_stop_col] < merge_stop_val)
# merging = any(seg.geometry.area < merge_stop_val) # make function to check if merging needed

# # Column to skip merging if no candidates found
# seg[skip_merge] = False

# # Change to while
# # check if any features in gdf don't meet merge stop criteria, (while) - merge()
# iteration=0
# while merging:
    
#     # Create df of all features to be merged
#     subset = create_subset(gdf=seg, subset_col=subset_col, 
#                             subset_thresh=subset_thresh, 
#                             subset_compare=subset_compare)
#     # Remove any features marked to skip (no neighbors within merge threshold)
#     # subset = subset.merge(seg[[unique_id, skip_merge]], on=unique_id, how='left')
#     # subset[skip_merge] = subset[skip_merge].map(seg.set_index(uni))
#     # subset = subset[subset[skip_merge]==False]
    
#     # Get neighbors for all features to be merged
#     seg = get_neighbors(seg, subset=subset,
#                         unique_id=unique_id,
#                         neighbor_field=neighbor_fld)

#     # Get first row, feature to be merged
#     feat = subset.iloc[0:1,:]
#     feat_idx = feat.index.values[0]
    
#     # Get neighbors for feat
#     feat_id = feat[unique_id].values[0]
#     # feat[neighbor_fld] = seg.iloc[feat_idx,:][neighbor_fld]
    
#     # Check if feature has neighbor within merge threshold
#     # Value of merge column for feature
#     feat_val = feat[merge_col].values[0]
#     values = neighbor_values(feat, unique_id, feat[neighbor_fld], merge_col)
#     merge_candidates = {fid: val for fid, val in values.items()
#                         if feat_val-merge_thresh <= val <= feat_val+merge_thresh}
#     # If not matches, set skip column to true, skip merging
#     if len(merge_candidates) == 0:
#         seg.at[feat_idx, skip_merge] = True
#         continue
    
#     seg = merge(seg, unique_id, neighbor_fld, feat=feat,
#                 merge_col=merge_col, merge_thresh=merge_thresh)
#     # Remove these from original df
#     # Check if condition is met
#     merging = any(seg.geometry.area < merge_stop_val)
#     iteration+=1
#     print('iter: {}'.format(iteration))
#     print('id merged: '.format(feat_id))
    

# import matplotlib.pyplot as plt

# plt.style.use('ggplot')
# fig, ax = plt.subplots(1,1)
# should_merge.plot(ax=ax, facecolor='none', edgecolor='b', linewidth=2.5)
# seg.plot(ax=ax, facecolor='none', edgecolor='r', linewidth=0.5)

# x[unique_id] = x.index

# m = True
# x = 0
# s = 0
# while m:
#     s+=x
#     x+=1
#     if x == 2:
#         continue
#     print(x)
#     if s > 3:
#         m = False
    