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

import geopandas as gpd

from query_danco import query_footprint

# Paths to data
xtrack_path = r'C:/Users/disbr007/imagery/dg_cross_track_2019jan09_deliv.gdb'
pgc_path = 'pgc_imagery_catalogids_stereo' # layer name for query_danco fxn - layer with all P1BS ids
nasa_path = r"Y:\private\imagery\satellite\_footprints\ADAPT_catalog\20190219\nga_inventory20190219.gdb"
ordered_path = r"C:\Users\disbr007\imagery\not_onhand\all_ids_onhand.txt"

# Read data into geopandas
xtrack = gpd.read_file(xtrack_path, driver='OpenFileGDB', layer=1)
pgc = query_footprint(pgc_path)
nasa = gpd.read_file(nasa_path, driver='OpenFileGDB', layer=1)

# Create list of all onhand ids
# Create list of ordered ids - all IDs ever ordered -> from IMA
ordered = []
with open(ordered_path, 'r') as f:
    content = f.readlines()
    for line in content:
        ordered.append(line.strip())
        
# List of all pgc onhand ids
pgc_ids = list(pgc['catalogid'])

# List of all NASA onhand ids
nasa_ids = list(nasa['catalogid'])

# Create master list of 'onhand' ids
onhand = ordered + pgc_ids + nasa_ids

# Create column in xtrack df for onhand/notonhand
xtrack['onhand'] = (xtrack['catalogid1'].isin(onhand) & xtrack['catalogid2'].isin(onhand))

# Export xtrack as shapefile / featureclass

