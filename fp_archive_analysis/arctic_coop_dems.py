# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 13:13:23 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import seaborn as sns
import os
import matplotlib.pyplot as plt

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


def select_by_feat(in_lyr, target, target_name='Site Name', date_col='acqdate', cloud='cloudcover', catid='catalogid'):
    '''
    select features from in_lyr that intersects each feature in target
    in_lyr: geodataframe to select from
    target: geodataframe to base selection on
    (the following args defaults to dg_footprint params)
    date_col: column that holds date information
    cloud: column that holds cloud cover
    catid: catalogid column
    '''
#    # Do inital selection on all features in target to limit second searches
    initial_selection = select_location(in_lyr, target)
    
    # Create empty gdf to hold master selection
    cols = ['PAIRNAME', 'ACQDATE1', 'geometry', target_name]
    sel = gpd.GeoDataFrame(columns=cols)
    sel_ids = [] # empty list to hold ids, don't add if already in list
    sel.crs = in_lyr.crs
    
    # Define cols not to keep from target
    drop_cols = list(target)
    if 'geometry' in drop_cols:
        drop_cols.remove('geometry') # keep geometry in selection
        drop_cols.remove(target_name)
    drop_cols.append('index_right') # remove added index col
        
    # Select for each point
    target.reset_index(inplace=True)
    for i in range(len(target)): # loop each feature/row in target
        feat = target.loc[[i]] # current feature
        
        # Spatial join for current feature
        sel4feat = gpd.sjoin(initial_selection, feat, how='inner', op='intersects') # select by location
        
        # Add column noting which feature in target this was selected for
        name = feat[target_name].to_string(index=False)
        sel4feat[target_name] = name
        
        # Remove unnec. columns
        for col in list(sel4feat):
            if col not in cols:
                sel4feat.drop([col], axis=1, inplace=True) # remove unnecc cols    
        
        # Ensure no DUPs
        sel_id = sel4feat[catid].iloc[0] # get catalog id of selection
        if sel_id not in sel_ids:
            sel_ids.append(sel_id)
        
        # Combine master with current features selection
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

# Select DEMs over each site
dems_by_feat = select_by_feat(dems, sites, target_name='SiteName', date_col='ACQDATE1', catid='PAIRNAME')

# Aggregrate by site and year
dems_by_feat['ACQDATE1'] = pd.to_datetime(dems_by_feat['ACQDATE1']) # convert to datetime col
dems_by_feat.set_index(['ACQDATE1'], inplace=True)
dems_by_feat['Year'] = dems_by_feat.index.year
dems_agg = dems_by_feat.groupby(['Year', 'SiteName']).agg({'Year': 'count'})
dems_agg = dems_agg.unstack()
dems_agg = dems_agg.transpose()
dems_agg.index = dems_agg.index.droplevel(level=0)

min_val = dems_agg.min(axis=1).min()
max_val = dems_agg.max(axis=1).max()

cols = list(dems_agg)
dems_agg['Total'] = dems_agg[cols].sum(axis=1)

sns.heatmap(dems_agg, cmap='Reds', fmt='.0f', 
            linewidths=0.2, linecolor='lightgrey', 
            annot=True, vmin=min_val, vmax=max_val).set_title('PGC Processed DEMs')
plt.tick_params(
        axis='both',
        which='both',
        bottom=False,
        left=False,
        )
plt.tight_layout()


# Join back to target to write shapefile with counts
sites.set_index('SiteName', inplace=True)
dems_agg = dems_agg.join(sites)
dems_agg = dems_agg.set_geometry('geometry')
cols = list(dems_agg)
cols.remove('geometry')
for col in cols:
    dems_agg[col] = dems_agg[col].astype(str)
#dems_agg.to_file(os.path.join(project_path, 'selection_sites_count.shp'), driver='ESRI Shapefile') - encoding/type error...



