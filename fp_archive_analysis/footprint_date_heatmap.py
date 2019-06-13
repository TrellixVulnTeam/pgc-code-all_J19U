# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 13:13:23 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import seaborn as sns
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os, argparse, time

from query_danco import query_footprint, list_danco_footprint

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


def select_by_feat(target, in_lyr, target_name='Site Name', 
                   date_col='acqdate', 
                   date_min=None, 
                   date_max=None, 
                   catid='catalogid',
                   cloudcover_col='cloudcover'):
    '''
    select features from in_lyr that intersects each feature in target
    in_lyr: geodataframe to select from
    target: geodataframe to base selection on
    (the following args defaults to dg_footprint params)
    target_name: column from target dataset to keep
    date_col: column that holds date information
    date_min: earliest date to choose (default no min)
    date_max: latest date to choose (default no max)
    catid: catalogid column
    cloudcover_col: column with cloudcover info
    '''
    # Select only within date range
    in_lyr = in_lyr[(in_lyr[date_col] >= date_min) & (in_lyr[date_col] <= date_max)]
    
    # Do inital selection on all features in target to limit secondary searches
    initial_selection = select_location(in_lyr, target)
    print('Total matches over all AOI features: {}'.format(len(initial_selection)))
    
    # Create empty gdf to hold master selection
    cols = [catid, date_col, 'geometry', target_name, cloudcover_col]
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


def agg_by_year(fp, aoi_id, date_col, freq, catid='PAIRNAME'):
    '''
    Takes a dataframe that is a footprint selection over each AOI point and aggregates by 
    time period (year, month, day) and AOI point
    fp: dataframe with all ids for each point
    date_col: name of dataframe column holding date
    freq: frequency to group by ('Y', 'M', 'W' 'D')
    '''
    ## Aggregrate by site and year
    # Convert to datetime
    fp[date_col] = pd.to_datetime(fp[date_col]) # convert to datetime col
    fp.set_index([date_col], inplace=True)
    
    # Aggregate by time period and feature
#    dems_by_feat['Year'] = dems_by_feat.index.year
    dems_agg = fp.groupby([pd.Grouper(freq=freq), aoi_id]).agg({catid: 'count'})
    # Moves SiteName out of index to column, then switches SiteName back to index
    dems_agg = dems_agg.unstack().resample(freq).asfreq()
    dems_agg = dems_agg.transpose()
    # Removes time period from index
    dems_agg.index = dems_agg.index.droplevel(level=0)
    
    # Convert columns to datetime object
    dems_agg.columns = pd.to_datetime(dems_agg.columns, format='%Y-%m-%d %H:%M:%S')
    
    
    # Format correctly for freq
    if freq == 'Y':
        dems_agg.columns = dems_agg.columns.year
    elif freq == 'M':
        dems_agg.columns = dems_agg.columns.map(lambda x: x.strftime('%Y %b'))
    elif freq == 'W':
        dems_agg.columns = dems_agg.columns.map(lambda x: x.strftime('%Y %b %d Week: %U')) # Week number out of year (may not work at all)
    elif freq == 'D':
        dems_agg.columns = dems_agg.columns.day

    return dems_agg
    

def plot_heatmap(agg_df, title, save_path=None):
    '''
    Takes an dataframe aggregated by AOI site and time period and creates a heatmap from it
    agg_df: dataframe aggregated by AOI site and time period
    title: title for heatmap plot
    '''
    ## Plot
    fig, ax = plt.subplots(figsize=(20,8))
        
    # Get min and max counts for setting limits
    min_val = agg_df.min(axis=1).min()
    max_val = agg_df.max(axis=1).max()
    
    # Get column names (time periods) and sum to create a 'Total' column
#    cols = list(agg_df)
#    agg_df['Total'] = agg_df[cols].sum(axis=1)
    
    hm = sns.heatmap(agg_df, cmap='Reds', fmt='.0f', 
                linewidths=0.2, linecolor='lightgrey', 
                annot=True, vmin=min_val, vmax=max_val, ax=ax).set_title(title) #xticklabels=2 (every other)
    
    ax.tick_params(
            axis='both',
            which='both',
            bottom=False,
            left=False,
            )
    
    fig.tight_layout()
    
    # Save plot
    if save_path:
        fig.savefig(save_path)
    
    return hm


def write_shp(agg_df, out_path):
    '''
    Write a copy of the original shapefile with counts per feature
    agg_df: aggregated dataframe
    out_path: path to write shapefile
    '''


def load_data(aoi, footprint):
    '''
    Load aoi and footprint layers. 
    aoi: shapefile of aoi features
    footprint: footprint layer to count -> can be shapefile or danco layer
    '''
    driver='ESRI Shapefile'
    aoi = gpd.read_file(aoi, driver=driver)
    if os.path.isfile(footprint):
        fp = gpd.read_file(footprint, driver=driver)
    elif type(footprint) == str:
        if footprint in list_danco_footprint():
            fp = query_footprint(layer=footprint)
    else:
        print('Unknown footprint type')
        fp = None
    return aoi, fp
        
    

#project_path = 'E:\disbr007\change_detection'
#
#sites_path = os.path.join(project_path, 'inital_site_selection.shp')
#dems_path = os.path.join(project_path, 'inital_site_selection_DEMs.shp')
#
## Load data
#aoi, fp = load_data(sites_path, dems_path)
#
## Select DEMs over each site
#dems_by_feat = select_by_feat(aoi, fp, target_name='SiteName', date_col='ACQDATE1', catid='PAIRNAME')
#
## Aggregrate by site and year
#agg = agg_by_year(dems_by_feat, date_col='ACQDATE1', freq='M', catid='PAIRNAME')
#
## Plot
#plot_heatmap(agg, title='Test')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('aoi', type=str, help='Path to AOI shapefile.')
    parser.add_argument('footprint', type=str, 
                        help='Path to footprint layer to use. Can be .shp or danco layer name. E.g.: "dg_imagery_index_stereo_onhand_cc20"')
    parser.add_argument('freq', type=str, 
                        help='Frequency to group by. Can be year ("Y"), month ("M"), week ("W"), or day ("D")')
    parser.add_argument('aoi_id', type=str, 
                        help='Name of column to identify AOI features.')
    parser.add_argument('fp_id', type=str,
                        help='Identifier to count in footprint. E.g. "CATALOG_ID" or "PAIRNAME", etc.')
    parser.add_argument('date_col', type=str,
                        help='Name of column in footprint specifying date')
    parser.add_argument('--date_min', type=str,
                        help='Earliest date to consider. E.g. "2007-01-31"')
    parser.add_argument('--date_max', type=str,
                        help='Latest date to consider. E.g. "2019-01-31"')
    
    args = parser.parse_args()
    if not args.date_min:
        date_min = dt.date.min.strftime('%Y-%m-%d')
    else:
        date_min = args.date_min
    if not args.date_max:
        date_max = dt.datetime.now().strftime('%Y-%m-%d')
    else:
        date_max = args.date_max
    
    ## RUN
    # Load data
    aoi, fp = load_data(args.aoi, args.footprint)
    # Select over each site
    fp_by_feat = select_by_feat(aoi, fp, 
                                target_name=args.aoi_id, 
                                date_col=args.date_col, 
                                date_min=date_min, 
                                date_max=date_max,
                                catid=args.fp_id)
    # Aggregate by feature in aoi and frequency
    agg = agg_by_year(fp_by_feat, aoi_id=args.aoi_id, date_col=args.date_col, freq=args.freq, catid=args.fp_id)
    # Plot
    plot_heatmap(agg, title='Test', save_path='test2.png')



# Join back to target to write shapefile with counts
#sites.set_index('SiteName', inplace=True)
#dems_agg = dems_agg.join(sites)
#dems_agg = dems_agg.set_geometry('geometry')
#cols = list(dems_agg)
#cols.remove('geometry')
#for col in cols:
#    dems_agg[col] = dems_agg[col].astype(str)
#dems_agg.to_file(os.path.join(project_path, 'selection_sites_count.shp'), driver='ESRI Shapefile') - encoding/type error...