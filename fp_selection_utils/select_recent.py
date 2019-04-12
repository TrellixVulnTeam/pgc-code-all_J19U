# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 10:14:18 2019

@author: disbr007

Select most recent features from an input layer over each point in a point or
line layer AOI
Adding support for polygons

"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os

from query_danco import query_footprint

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

def line2pts(poly, interval, write_path=False):
    '''
    takes a geodataframe that has line geometry and returns points along the 
    line at the specified interval, where interval is a fraction of the line length
    poly: geodataframe with line geometry
    interval: fraction of length of line to create points at
    '''
    nodes = gpd.GeoDataFrame(columns=['pts'])
    for i in np.arange(0.0, 1.0, interval):
        node = gpd.GeoDataFrame(columns=['pts'])
        pt = poly.geometry.interpolate(i, normalized=True)
        node['pts'] = pt
        nodes = merge_gdf(nodes, node)
    
    nodes.set_geometry('pts', inplace=True)
    nodes.crs = poly.crs
    if write_path:
        nodes.to_file(write_path, driver=driver)
    return nodes

def select_recent(in_lyr, target, date_col='acqdate', cloud='cloudcover', catid='catalogid'):
    '''
    select most recent feature from in_lyr that intersects each feature in target
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
        latest = sel4feat[date_col].max() # get most recent date
        sel4feat = sel4feat[sel4feat[date_col] == latest] # keep only most recent selection
        # if the date is the same for multiple selections, use other criteria
        if len(sel4feat) > 1:
            min_cc = sel4feat[cloud].min()
            sel4feat = sel4feat[sel4feat[cloud] == min_cc]
            if len(sel4feat) > 1:
                sel4feat = sel4feat.iloc[[0]]
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
    

project_path = r'E:\disbr007\UserServicesRequests\Projects\1518_pfs'
working_dir = os.path.join(project_path, '3694_gulley_imagery', 'project_files')

trav_path = os.path.join(project_path, 'pfs_crrel_traverse_routes_2019.shp')
pts_path = os.path.join(project_path, 'pfs_crrel_field_points_2019.shp')

driver = 'ESRI Shapefile'
# Read AOIs
pts = gpd.read_file(pts_path, driver=driver)
trav = gpd.read_file(trav_path, driver=driver)

# Select only relevent points and travs
#renn_pts = pts[pts.Team == 'Rennermalm']
#renn_trav = trav[trav.Team == 'Rennermalm']
pts = pts[pts.Team == 'Gulley']
#trav = trav[trav.Team == 'Gulley']

# Get DEM source layers
source = query_footprint('dg_imagery_index_stereo_onhand_cc20 selection')
source_cols = list(source)
crs = source.crs

# Get imagery source layers
#img_idx_path = r'E:\disbr007\UserServicesRequests\Projects\1518_pfs\idx_pts_2017_present.shp'
#source = gpd.read_file(img_idx_path)

# Create points for line layers at specified interval along line
#renn_trav_pts = line2pts(renn_trav, 0.05, write_path=os.path.join(working_dir, 'nodes.shp'))
#trav_pts = line2pts(trav, 0.05, write_path=os.path.join(working_dir, 'trav_pts.shp'))

# Find most recent for each feature
#sel_dems_pts = select_recent(stereo_oh, renn_pts, catid='pairname')
#sel_dems_trav = select_recent(stereo_oh, renn_trav_pts, catid='pairname')
selection = select_recent(source, pts) #, catid='CATALOG_ID', date_col='ACQ_TIME', cloud='CLOUDCOVER')

# Write selection to shapefile
#sel_dems_pts.to_file(os.path.join(working_dir, 'sel_dems_test_pts.shp'), driver=driver)
#sel_dems_trav.to_file(os.path.join(working_dir, 'sel_dems_test_trav.shp'), driver=driver)
selection.to_file(os.path.join(working_dir, 'gulley_dem_selection.shp'), driver=driver)


### ORIGINAL SCRIPT BELOW FOR REFERNCE ###
#stereo_oh_pts = gpd.sjoin(stereo_oh, renn_pts, how='inner', op='intersects')
#drop_cols = list(pts)
#drop_cols.remove('geometry')
#drop_cols.append('index_right')
#stereo_oh_pts.drop(drop_cols, axis=1, inplace=True)

#sel_dems = gpd.GeoDataFrame(columns=stereo_cols)
#sel_ids = []
#for i in range(len(renn_pts)):
#    print(i)
#    pt = renn_pts.loc[[i]]
#    oh = gpd.sjoin(stereo_oh_pts, pt, how='inner', op='intersects')
#    oh.drop(drop_cols, axis=1, inplace=True)
#    latest = oh['acqdate'].max()
#    recent_oh = oh[oh['acqdate'] == latest]
#    if len(recent_oh) > 1:
#        min_cc = recent_oh['cloudcover'].min()
#        recent_oh = recent_oh[recent_oh['cloudcover']== min_cc]
#        if len(recent_oh) > 1:
#            min_area = recent_oh['sqkm'].min()
#            recent_oh = recent_oh[recent_oh['sqkm']== min_area]
#            if len(recent_oh) > 1:
#                recent_oh = recent_oh.iloc[[0]]
#    print(recent_oh)
#    sel_id = recent_oh['catalogid'].iloc[0]
#    if sel_id not in sel_ids:
#        sel_ids.append(sel_id)
#        sel_dems = merge_gdf(sel_dems, recent_oh)
#
#sel_dems.set_geometry('geom', inplace=True)
#sel_dems.crs = crs