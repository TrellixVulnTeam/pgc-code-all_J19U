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
import sys, os, argparse, multiprocessing
from joblib import Parallel, delayed

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids
#from gpd_utils import multiprocess_mfp


def select_from_mfp(index_path, ids_of_int_path, field):
        
    ## Get all ids of interest
    ids_of_int = read_ids(ids_of_int_path)
    
    ## Name of database and master footprint -> remove
    layers = fiona.listlayers(index_path)    
    index_basename = os.path.basename(index_path).split('.')[0]
    layers.remove(index_basename)
    
    select_dfs = [] # storing all ids
    ## Get selection from subset of index
    for layer in tqdm.tqdm(layers):
        index_subset = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
#        print(list(index_subset))
        index_select = index_subset[index_subset[field].isin(ids_of_int)]
        select_dfs.append(index_select)
    
    selection = pd.concat([select_dfs], ignore_index=True)
    
    return selection



#def select_from_mfp(layer, index_path, ids_of_int_path, field):
#    
#    ids_of_int = read_ids(ids_of_int_path)    
#    index_subset = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
#    index_select = index_subset[index_subset[field].isin(ids_of_int)]
#    
#    return index_select
#
#
#def multiprocess_mfp(fxn, *args, num_cores=None, **kwargs):
#    num_cores = num_cores if num_cores else multiprocessing.cpu_count() - 4
#    print(num_cores)
#    
#    index_path = "C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb"
#    
#    ## Name of database and master footprint -> remove
#    layers = fiona.listlayers(index_path)    
#    index_basename = os.path.basename(index_path).split('.')[0]
#    layers.remove(index_basename)
#    
#    # Run fxn in counts
#    results = Parallel(n_jobs=num_cores)(delayed(fxn)(layer, *args, **kwargs) for layer in tqdm.tqdm(layers))
#    
#    # Combine individual gdfs back into one
#    output = pd.concat(results)
#
#    return output



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('ids_path', type=str, 
                        help='Path to ids of interest')
    parser.add_argument('field', type=str,
                        help='Field in ids path. E.g. "SCENE_ID", "CATALOG_ID"')
    parser.add_argument('out_path', type=str,
                        help='Path to write shp of selection to.')
    
    args = parser.parse_args()
    
    index_path = "C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb"
#    df = multiprocess_mfp(select_from_mfp, index_path, args.ids_path, args.field)
    df = select_from_mfp(index_path, args.ids_path, args.field)
    df.to_file(os.path.abspath(args.out_path), driver='ESRI_Shapefile')


    
