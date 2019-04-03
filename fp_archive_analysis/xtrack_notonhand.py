# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 11:44:48 2019

@author: disbr007
xtrack pairs onhand / notonhand
onhand defined as at PGC or NASA or ordered

xtrack all: dg_cross_track_2019jan09_deliv.gdb (made by Claire)
at PGC: danco.footprint.sde.pgc_imagery_catalogids_stereo
at NASA: ADAPT footprint - Y:\private\imagery\satellite\_footprints\ADAPT_catalog\20190219
ordered: Danny makes a txt of all catalogids that have ever been ordered
"""

import os
import geopandas as gpd
import pandas as pd

from query_danco import query_footprint

# Paths to data
xtrack_path = r'C:/Users/disbr007/imagery/dg_cross_track_2019jan09_deliv.gdb'
pgc_path = 'pgc_imagery_catalogids_stereo' # layer name for query_danco fxn - layer with all P1BS ids
#nasa_path = r"C:\Users\disbr007\imagery\nga_inventory20190219.gdb" # Feature class
nasa_path = r"C:\Users\disbr007\imagery\nasa_adapt_nga_inventory_20190219.txt" # exported table in arc as text
ordered_path = r"C:\Users\disbr007\imagery\not_onhand\all_ids_onhand.txt"

# Read data into geopandas/pandas
xtrack = gpd.read_file(xtrack_path, driver='OpenFileGDB', layer='dg_imagery_index_all_cc20_xtrack_pairs_jan09_prj_WGS', crs = {'init': 'espg:4326'})
print('xtrack loaded into gpd...')
pgc = query_footprint(pgc_path, table=True)
print('pgc loaded into gpd...')
#nasa = gpd.read_file(nasa_path, driver='OpenFileGDB', layer='nga_inventory20190219')

# Read nasa in chunks
counter = 0
chunksize = 10**5
nasa_ids = []
for chunk in pd.read_csv(nasa_path, chunksize=chunksize):
    ids = list(chunk['CATALOG_ID'])
    for e in ids:
        nasa_ids.append(e)
    counter += chunksize
    if counter % 10**6 == 0:
        print(counter)
print('NASA ids read into list..')

# Create list of all onhand ids
# Create list of ordered ids - all IDs ever ordered -> from IMA
ordered = []
with open(ordered_path, 'r') as f:
    content = f.readlines()
    for line in content:
        ordered.append(line.strip())
        
# List of all pgc onhand ids
pgc_ids = list(pgc['catalog_id'])

# List of all NASA onhand ids
#nasa_ids = list(nasa['catalogid'])

# Create master list of 'onhand' ids
onhand = ordered + pgc_ids + nasa_ids
set_onhand = list(set(onhand))

# Create columns in xtrack df for onhand/notonhand for each id and for both
xtrack['id1_onhand'] = xtrack['catalogid1'].isin(set_onhand) # id1 is in on hand ids list
xtrack['id2_onhand'] = xtrack['catalogid2'].isin(set_onhand) # id2 is in on hand ids list
xtrack.loc[(xtrack['id1_onhand'] & xtrack['id2_onhand']), 'onhand'] = True # both ids are on hand
xtrack[['onhand']] = xtrack[['onhand']].fillna(False) # Turn NaN values to false
# Convert True, False values to int for exporting to shapefile - shp doesn't support Boolean
cols2conv = ['id1_onhand', 'id2_onhand', 'onhand']
for col in cols2conv:
    xtrack[col] = xtrack[col].astype(int)


# Export xtrack as shapefile / featureclass
print('writing to shapefile...')
out_path = r'C:\Users\disbr007\imagery\xtrack_onhand'
xtrack.to_file(out_path, driver='ESRI Shapefile')
xtrack.to_pickle(os.path.join(out_path, 'xtrack.pkl'))
print('done')