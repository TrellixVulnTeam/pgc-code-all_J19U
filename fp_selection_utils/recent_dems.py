# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 10:14:18 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

from query_danco import query_footprint

def merge_gdf(gdf1, gdf2):
    gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True), crs=gdf1.crs)
    return gdf

def select_recent(in_lyr, target, date_col='acqdate', cloud='cloudcover', catid='catalogid'):
    # Create empty gdf to hold selection
    cols = list(in_lyr)
    sel = gpd.GeoDataFrame(columns=cols)
    sel_ids = [] # empty list to hold ids, don't add if already in list
    sel.crs = in_lyr.crs
    
    # Define cols not to keep from target
    drop_cols = list(target)
    drop_cols.remove('geometry') # keep geometry in selection
    drop_cols.append('index_right') # remove added index col
        
    for i in range(len(target)): # loop each feature/row in target
        feat = target.loc[[i]] # current feature
        sel4feat = gpd.sjoin(in_lyr, feat, how='inner', op='intersects') # select by location
        sel4feat.drop(drop_cols, axis=1, inplace=True) # remove unnecc cols    
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
    
    sel.set_geometry('geom', inplace=True)
    return sel
    

project_path = r'E:\disbr007\UserServicesRequests\Projects\1518_pfs'
working_dir = os.path.join(project_path, '3690_rennermalm_dems', 'project_files')

trav_path = os.path.join(project_path, 'pfs_crrel_traverse_routes_2019.shp')
pts_path = os.path.join(project_path, 'pfs_crrel_field_points_2019.shp')

driver = 'ESRI Shapefile'
pts = gpd.read_file(pts_path, driver=driver)
trav = gpd.read_file(trav_path, driver=driver)

renn_pts = pts[pts.Team == 'Rennermalm']
renn_trav = trav[trav.Team == 'Rennermalm']

stereo_oh = query_footprint('dg_imagery_index_stereo_onhand_cc20 selection')
stereo_cols = list(stereo_oh)
crs = stereo_oh.crs

# Do initial select by location on all pts to limit the per point search
def select_location(in_lyr, target):
    # Define colums to drop from target
    drop_cols = list(target)
    drop_cols.remove('geometry')
    drop_cols.append('index_right')
    
    
    selection = gpd.sjoin(in_lyr, target, how='inner', op='intersects')
    
    
    
stereo_oh_pts = gpd.sjoin(stereo_oh, renn_pts, how='inner', op='intersects')
drop_cols = list(pts)
drop_cols.remove('geometry')
drop_cols.append('index_right')
stereo_oh_pts.drop(drop_cols, axis=1, inplace=True)

sel_dems = select_recent(stereo_oh_pts, renn_pts)

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
sel_dems.to_file(os.path.join(working_dir, 'sel_dems_test.shp'), driver=driver)
    