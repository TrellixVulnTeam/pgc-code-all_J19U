# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 12:02:39 2019

@author: disbr007
Select by ids from PGC master footprint
"""

import geopandas as gpd
import fiona
import pandas as pd
import tqdm
import sys, os, argparse, multiprocessing, logging
from joblib import Parallel, delayed

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids


## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


## CURRENT PATH TO MASTER FOOTPRINT ##
index_path = "C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb"


def select_from_mfp(ids_of_int_path, field):
    global index_path
    ## Get all ids of interest
    ids_of_int = read_ids(ids_of_int_path)
    
    ## Name of database and master footprint -> remove
    layers = fiona.listlayers(index_path)    
    index_basename = os.path.basename(index_path).split('.')[0]
    layers.remove(index_basename)
    print(layers)
    
    
    select_dfs = [] # storing all ids
    ## Get selection from subset of index
    for layer in tqdm.tqdm(layers):
        index_subset = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
#        print(list(index_subset))
        index_select = index_subset[index_subset[field].isin(ids_of_int)]
        select_dfs.append(index_select)
    
    selection = pd.concat([select_dfs], ignore_index=True)
    
    return selection


def mfp_layers_subset(lat_min, lat_max):
    '''
    Given that the mfp has been split into latitude sections - returns only
    those layer names within the latitude range provided
    '''
    global index_path
    lat_range = range(lat_min-1, lat_max+1)

    # Get all layer names from MFP GDB, remove original MFP    
    layers = fiona.listlayers(index_path)    
    index_basename = os.path.basename(index_path).split('.')[0]
    layers.remove(index_basename)
    
    # Create dict to store lat_range: layer for each layer
    lyr_dict = {}
    for layer in layers:
        key = layer.split('_')
        key = key[-2:]
        for i in key:
            low = key[0].replace('neg', '-')
            high = key[1].replace('neg', '-')
        key = (int(low), int(high))
        lyr_dict[key] = layer
    
    # Find all layers that match the provided range
    lyr_matches = []
    for k, v in lyr_dict.items():
        lyr_range = range(k[0], k[1])
        for r in lyr_range:
            if r in lat_range:
                lyr_matches.append(v)
                break
            
    return lyr_matches


def mfp_subset(lat_min, lat_max):
    dfs = []
    layers = mfp_layers_subset(lat_min, lat_max)
    logging.info('Reading relevant master footprint layers into geodataframes...')
    for layer in tqdm.tqdm(layers):
        df = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
        dfs.append(df)
    return dfs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('ids_path', type=str, 
                        help='Path to ids of interest')
    parser.add_argument('field', type=str,
                        help='Field in ids path. E.g. "SCENE_ID", "CATALOG_ID"')
    parser.add_argument('out_path', type=str,
                        help='Path to write shp of selection to.')
    
    args = parser.parse_args()
    
    

    df = select_from_mfp(index_path, args.ids_path, args.field)
    df.to_file(os.path.abspath(args.out_path), driver='ESRI_Shapefile')


    
