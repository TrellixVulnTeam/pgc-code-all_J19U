# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 11:40:27 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import calendar, datetime, sys, os
from query_danco import stereo_noh, query_footprint

# Load data
all_oh = query_footprint('dg_imagery_index_all_onhand') # All ids onhand

intrack_noh = stereo_noh() # Intrack cc20 not on hand
intrack_noh = intrack_noh[['acqdate', 'catalogid']] # Drop all other columns

# All crosstrack
xtrack_gdb_path = r'C:\Users\disbr007\imagery\dg_cross_track_2019jan09_deliv.gdb'
xtrack = gpd.read_file(
        xtrack_gdb_path, 
        crs = {'init': 'espg:4326'}, 
        driver='OpenFileGDB', 
        layer='dg_imagery_index_all_cc20_xtrack_pairs_jan09_prj_WGS')

## Cross track both ids
# Get unique ids from both catalogid1 and catalogid2 columns
xtrack1_ids = set(list(xtrack.catalogid1.values))
xtrack2_ids = set(list(xtrack.catalogid2.values))
xtrack2_unq_ids = [x for x in xtrack2_ids if x not in xtrack1_ids]

# Create dataframes of ids in catid1 and catid2
xtrack1 = xtrack[['catalogid1', 'acqdate1', 'sqkm']][xtrack.catalogid1.isin(xtrack1_ids)]
xtrack2 = xtrack[['catalogid2', 'acqdate2', 'sqkm']][xtrack.catalogid2.isin(xtrack2_unq_ids)]

# Drop duplicate rows
xtrack1.drop_duplicates('catalogid1', keep='first', inplace=True)
xtrack2.drop_duplicates('catalogid2', keep='first', inplace=True)

# Rename for concat
xtrack1.rename(index=str, columns={'catalogid1': 'catalogid', 'acqdate1': 'acqdate'}, inplace=True)
xtrack2.rename(index=str, columns={'catalogid2': 'catalogid', 'acqdate2': 'acqdate'}, inplace=True)

# Add catid1 and catid2 dataframes to get unique xtrack ids and acqdates
xtrack_unq = pd.concat([xtrack1, xtrack2])

# Cross track not onhand
ids_oh = list(all_oh.catalogid) # list of all IDs onhand
xtrack_noh = xtrack_unq[~xtrack_unq.catalogid.isin(ids_oh)] # all xtrack ids not onhand

# Monthly grouping
intrack_noh['acqdate'] = pd.to_datetime(intrack_noh['acqdate'])
xtrack_noh['acqdate'] = pd.to_datetime(xtrack_noh['acqdate'])

intrack_noh.set_index('acqdate', inplace=True)
xtrack_noh.set_index('acqdate', inplace=True)

# Break out cross track area bins
xtrack_aggregation = {'catalogid': 'nunique', 'sqkm': 'sum'}
monthly_xtrack_noh = xtrack_noh.groupby(pd.Grouper(freq='M')).agg(xtrack_aggregation)
monthly_xtrack_1k = xtrack_noh[xtrack_noh['sqkm'] >= 1000.0].groupby(pd.Grouper(freq='M')).agg(xtrack_aggregation)
monthly_xtrack_500 = xtrack_noh[(xtrack_noh['sqkm'] >= 500.0) & (xtrack_noh['sqkm'] < 1000.0)].groupby(pd.Grouper(freq='M')).agg(xtrack_aggregation)
monthly_xtrack_250 = xtrack_noh[(xtrack_noh['sqkm'] >= 250.0) & (xtrack_noh['sqkm'] < 500.0)].groupby(pd.Grouper(freq='M')).agg(xtrack_aggregation)
monthly_xtrack_0 = xtrack_noh[xtrack_noh['sqkm'] < 250.0].groupby(pd.Grouper(freq='M')).agg(xtrack_aggregation)

monthly_intrack_noh = intrack_noh.groupby(pd.Grouper(freq='M')).agg({'catalogid': 'nunique'})

# Output to excel
final_dfs = {
#        'intrack_noh': monthly_intrack_noh,
#        'xtrack_noh': monthly_intrack_noh,
        'xtrack_1k': monthly_xtrack_1k,
        'xtrack_500': monthly_xtrack_500,
        'xtrack_250': monthly_xtrack_250,
        'xtrack_0': monthly_xtrack_0}

col_rename = { 
        'acqdate': 'Date', 
        'catalogid': 'Strips', # intrack strips column
        'sqkm': 'Area (sq. km)',  # intrack and xtrack area col
        'pairname': 'Pairs',  # xtrack pairs column
        'catalogid1': 'Unique Strips', # xtrack unique ids column
        'arctic': 'Arctic', 
        'antarctica': 'Antarctica', 
        'nonpolar': 'Non-Polar'
        }


out_path = r'C:\Users\disbr007\imagery\not_onhand\not_onhand.xlsx'
excel_writer = pd.ExcelWriter(out_path)
for name, df in final_dfs.items():
    final_dfs[name].reset_index(inplace=True)
    final_dfs[name].rename(index=str, columns=col_rename, inplace=True)
    final_dfs[name]['Month'] = final_dfs[name]['Date'].dt.month
    final_dfs[name]['Month'] = final_dfs[name]['Month'].apply(lambda x: calendar.month_abbr[x])
    final_dfs[name]['Year'] = final_dfs[name]['Date'].dt.year
    if name == 'intrack_noh':
        pass
    else:
        final_dfs[name]['Node Hours'] = final_dfs[name]['Area (sq. km)'].div(16.)
    df.to_excel(excel_writer, name, index=True)
excel_writer.save()
