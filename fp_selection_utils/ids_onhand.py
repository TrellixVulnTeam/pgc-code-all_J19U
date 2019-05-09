# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 12:02:39 2019

@author: disbr007
Select by ids from PGC master footprint
"""

import geopandas as gpd
import fiona
import pandas as pd
from tqdm import tqdm
import sys, os

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids

def determine_onhand(ids, onhand_ids):
    oh = [x for x in ids if x in onhand_ids]
    noh = [x for x in ids if x not in onhand_ids]
    return oh, noh


# Path to master footprint
index_path = r"E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19.gdb"
# Path to ids of interest
ids_of_int_path = r''

## Get all ids from the master footprint
# Get all layers in GDB
layers = fiona.listlayers(index_path)

# Name of database and master footprint -> remove
index_basename = os.path.basename(index_path).split('.')[0]
layers.remove(index_basename)

index_ids = [] # storing all ids
total_count = 0 # for confirming all ids have been parsed
for layer in tqdm(layers):
    index_subset = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
    subset_ct = len(index_subset)
    ids = list(set(list(index_subset['CATALOG_ID'])))
    index_ids.append(ids)

## Get all ids of interest
ids_of_int = read_ids(ids_of_int_path)

## Determine on hand and not on hand ids
oh, noh = determine_onhand(ids_of_int, index_ids)

    
