# -*- coding: utf-8 -*-
"""
Created on Wed Apr 10 15:09:06 2019

@author: disbr007
Remove duplicate IDs from shapefile
"""

import pandas as pd
import geopandas as gpd
import os, sys, time
from tqdm import tqdm

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids

def remove_dups(shp, ordered, catid='catalogid', outpath=None):
    '''
    shp: input shapefile to remove dups from
    ordered: path to directory holding ordered ids as .txt or .csv
    catid: catalog id field name, defaults to danco/DG field name
    outpath: writing a new shapefile is desired, specify out path
    '''
    # Specify type of shp
    driver = 'ESRI Shapefile'
    
    # Get source ids
    source = gpd.read_file(shp, driver=driver)
    source_ids = list(source[catid].unique())
    print('Source IDs: {}'.format(len(source_ids)))
    
    # Get ordered ids
    ordered_ids = []
    files = [file for file in os.listdir(ordered)]
    for file in files:
        file_path = os.path.join(ordered, file)
        file_ids = read_ids(file_path)
        for x in file_ids:
            x = x.split(',')[0]
            ordered_ids.append(x)
    print('Previously ordered IDs: {}'.format(len(ordered_ids)))
            
    # Remove DUPs
    dups = [x for x in source_ids if x in ordered_ids]
    no_dups = [x for x in source_ids not in ordered_ids]
    
    return no_dups, dups

    
selection = r"E:\disbr007\imagery_orders\PGC_order_2019apr11_polar_hma_above_refresh\PGC_order_2019apr11_polar_hma_above_refresh.shp"
ordered = r'E:\disbr007\imagery_orders\ordered'

shp = selection
driver = 'ESRI Shapefile'

# Get source ids
source = gpd.read_file(shp, driver=driver)
source_ids = list(source['catalogid'].unique())
print('Source IDs: {}'.format(len(source_ids)))

# Get ordered ids
ordered_ids = []
files = [file for file in os.listdir(ordered)]
for file in files:
    file_path = os.path.join(ordered, file)
    file_ids = read_ids(file_path)
    for x in file_ids:
        x = x.split(',')[0]
        ordered_ids.append(x)
    print('Reading ordered IDs from file: {}'.format(len(ordered_ids)))
        
# Remove DUPs
source_ids.sort()
ordered_ids.sort()
dups = [x for x in tqdm(source_ids) if x in ordered_ids]
no_dups = [x for x in tqdm(source_ids) if x not in ordered_ids]
