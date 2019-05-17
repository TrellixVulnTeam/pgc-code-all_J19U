# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 12:02:39 2019

@author: disbr007
Select by ids from PGC master footprint
"""

import geopandas as gpd
import numpy as np
import fiona
import pandas as pd
from tqdm import tqdm
import sys, os

from query_danco import query_footprint
sys.path.insert(0,'C:\code\misc_utils')
from id_parse_utils import read_ids, write_ids


## IDs onhand - from pgc index
# Path to master footprint
#index_path = r"E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19.gdb"

## Get all ids from the master footprint
# Get all layers in GDB
#layers = fiona.listlayers(index_path)
# Name of database and master footprint -> remove
#index_basename = os.path.basename(index_path).split('.')[0]
#layers.remove(index_basename)

#selected_layers = ['pgcImageryIndexV6_2019mar19_60_80', 'pgcImageryIndexV6_2019mar19_80_100']
#
#index_ids = []
#for layer in tqdm(selected_layers):
#    index_subset = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
#    ids = list(set(list(index_subset['CATALOG_ID'])))
#    index_ids.append(ids)
    

## Get IDs we are comparing from text file 
# Store ids from multiple files in a single list    
#ids_of_int_path1 = r"E:\disbr007\UserServicesRequests\Projects\1539_CIRES_Herzfeld\3740\src\Negribreen_Glacier_DigitalGlobeIDs-v2.txt"
#ids_of_int_path2 = r"E:\disbr007\UserServicesRequests\Projects\1539_CIRES_Herzfeld\3740\src\Negribreen_Glacier_NSF_1745705_2017.txt"
#ids_of_int_paths = [ids_of_int_path1, ids_of_int_path2]
ids_of_int_paths = [r'E:\disbr007\UserServicesRequests\Projects\1539_CIRES_Herzfeld\3741\src\Bering_Glacier_DigitalGlobeIDs-v2.txt']

ids_of_int = []
for f in ids_of_int_paths:
    ## Get all ids of interest
    f_ids = read_ids(f, sep='\t')
    for i in f_ids:
        ids_of_int.append(i)

ids_tup = tuple(ids_of_int)

# Load geometry and other columns using index_dg footprint
where = "catalogid in {}".format(ids_tup)
index_dg = query_footprint(layer='index_dg', where=where)

## Determine oh - column
# Use PGC index subset to determine if on hand
#index_path = r'E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19_bering.shp'
index_path = r'E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19_bering.shp'
index = gpd.read_file(index_path, driver='ESRI Shapefile')
index_ids = list(set(index.CATALOG_ID))

# Add on hand column, 1 = True, 0 = False
index_dg['onhand'] = np.where(index_dg.catalogid.isin(index_ids), 1, 0)

## Write results
project_path = r'E:\disbr007\UserServicesRequests\Projects\1539_CIRES_Herzfeld\3741'
index_dg.sort_values(by='acqdate', inplace=True)
index_dg.to_file(os.path.join(project_path, 'CIRES_Herzfeld_bering_ids.shp'), driver='ESRI Shapefile')
csv_kwargs = {'columns':['catalogid', 'acqdate'], 'header':False, 'index':False, 'sep':'\t'}
index_dg[index_dg.onhand == 1].to_csv(os.path.join(project_path, 'onhand.csv'), **csv_kwargs)
index_dg[index_dg.onhand == 0].to_csv(os.path.join(project_path, 'not_onhand.csv'), **csv_kwargs)

# note: negribreen, missing id: 103001004761FC00
