# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 13:13:23 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

#from query_danco import query_footprint

def merge_gdf(gdf1, gdf2):
    gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True), crs=gdf1.crs)
    return gdf


def select_location(in_lyr, target):
    '''
    select features in 'in_lyr' that intersect 'target'
    in_lyr: geodataframe to select from
    target: geodataframe to base selection on - point geometry
    '''
    # Define colums to drop from target
    drop_cols = list(target)
    if 'geometry' in drop_cols:
        drop_cols.remove('geometry')
    drop_cols.append('index_right')
    
    selection = gpd.sjoin(in_lyr, target, how='inner', op='intersects')
    for col in drop_cols:
        if col in list(selection):
            selection.drop([col], axis=1, inplace=True)
    return selection


def select_recent(in_lyr, target, target_name='Site Name', date_col='acqdate', cloud='cloudcover', catid='catalogid'):
    '''
    select features from in_lyr that intersects each feature in target
    in_lyr: geodataframe to select from
    target: geodataframe to base selection on
    (the following args defaults to dg_footprint params)
    date_col: column that holds date information
    cloud: column that holds cloud cover
    catid: catalogid column
    '''
    # Do inital selection on all features in target to limit second searches
    initial_selection = select_location(in_lyr, target)
    
    # Create empty gdf to hold selection
    cols = list(in_lyr)
    sel = gpd.GeoDataFrame(columns=cols)
    sel_ids = [] # empty list to hold ids, don't add if already in list
    sel.crs = in_lyr.crs
    
    # Define cols not to keep from target
    drop_cols = list(target)
    if 'geometry' in drop_cols:
        drop_cols.remove('geometry') # keep geometry in selection
    drop_cols.append('index_right') # remove added index col
        
    # Select most recent
    target.reset_index(inplace=True)
    for i in range(len(target)): # loop each feature/row in target
        feat = target.loc[[i]] # current feature
        sel4feat = gpd.sjoin(initial_selection, feat, how='inner', op='intersects') # select by location
        for col in drop_cols:
            if col in list(sel4feat):
                sel4feat.drop([col], axis=1, inplace=True) # remove unnecc cols    
        
        sel_id = sel4feat[catid].iloc[0] # get catalog id of selection
        if sel_id not in sel_ids:
            sel_ids.append(sel_id)
            sel = merge_gdf(sel, sel4feat)
    
    # Set geometry column
    cols = list(sel)
    if 'geom' in cols:
        sel.set_geometry('geom', inplace=True)
    elif 'geometry' in cols:
        sel.set_geometry('geometry', inplace=True)
    return sel


project_path = 'E:\disbr007\change_detection'

sites_path = os.path.join(project_path, 'inital_site_selection.shp')
sites = gpd.read_file(sites_path, driver='ESRI_Shapefile')

dems_path = os.path.join(project_path, 'inital_site_selection_DEMs.shp')
dems = gpd.read_file(dems_path, driver='ESRI Shapefile')
