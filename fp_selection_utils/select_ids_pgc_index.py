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
#from joblib import Parallel, delayed
from pprint import pprint

#from id_parse_utils import read_ids


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
#index_path = r"C:\pgc_index\pgcImageryIndexV6_2019jun06_sliced.gdb"
index_path = r'C:\pgc_index\pgcImageryIndexV6_2019jun06_LAT30_LON60.gdb'


def select_from_mfp(ids_of_int_path, field):
    '''
    ## TO DO: Add lat / lon ranges to reduce number of footprints to search ##
    Selects given IDs from the masterfootprint
    '''
    global index_path
    ## Get all ids of interest
    ids_of_int = read_ids(ids_of_int_path)
    
    ## Name of database and master footprint -> remove
    layers = fiona.listlayers(index_path)    
    try:
        index_basename = os.path.basename(index_path).split('.')[0]
        layers.remove(index_basename)
    except ValueError:
        pass
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


def mfp_layers_subset(lon_min, lat_min, lon_max, lat_max):
    '''
    Given that the mfp has been split into latitude sections - returns only
    those layer names within the latitude range provided
    '''
    global index_path
    
    # Include provided mins/maxes
    lat_range = range(lat_min, lat_max)
    lon_range = range(lon_min, lon_max)
    
    # Get all layer names from MFP GDB, remove original MFP    
    layers = fiona.listlayers(index_path)    
    try:
        index_basename = os.path.basename(index_path).split('.')[0]
        layers.remove(index_basename)
    except ValueError:
        pass
    
    ## Create dict to store (lon_range, lat_range): layer name for each layer
    # Get all top right corners (max lats/lons) to determine step size
    lyr_dict = {}
    max_lons = []
    max_lats = []
    for layer in layers:
        max_lon, max_lat = layer.split('_')[-1], layer.split('_')[-2]
        max_lon = int(max_lon.replace('neg', '-').replace('LON', ''))
        max_lat = int(max_lat.replace('neg', '-').replace('LAT', ''))
        max_lons.append(max_lon)
        max_lats.append(max_lat)
        lyr_dict[layer] = {
                'max_lat': max_lat, 
                'max_lon': max_lon}
    
    max_lons = list(set(max_lons))
    max_lats = list(set(max_lats))

    max_lons = sorted(max_lons)
    max_lats = sorted(max_lats)
    
    lon_step = max_lons[1] - max_lons[0]
    lat_step = max_lats[1] - max_lats[0]


    lyr_matches = []
    for layer in layers:
        # Determine minimum of each layer given the step size
        lyr_dict[layer]['min_lat'] = lyr_dict[layer]['max_lat'] - lat_step
        lyr_dict[layer]['min_lon'] = lyr_dict[layer]['max_lon'] - lon_step
        
        # Find the range of each layer
        lyr_lat_range = range(lyr_dict[layer]['min_lat'], lyr_dict[layer]['max_lat'])
        lyr_lon_range = range(lyr_dict[layer]['min_lon'], lyr_dict[layer]['max_lon'])
        
        # Check if any lat or lon in the layers range are in the range of interest
        if any(i in lyr_lat_range for i in lat_range):
            if any(x in lyr_lon_range for x in lon_range):
                lyr_matches.append(layer)
                
    logging.info('Matching master footprint layers: {}'.format(lyr_matches))
    
    return lyr_matches


def mfp_subset(lon_min, lat_min, lon_max, lat_max):
    '''
    Yields masterfootprint subsets in given lat range as dataframes
    '''
    layers = mfp_layers_subset(lon_min, lat_min, lon_max, lat_max)
    logging.info('Matching master footprint layers: {}'.format(len(layers)))
    for layer in layers:
        print('Working on: {}'.format(layer))
        logging.info('Working on: {}'.format(layer))
        df = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
        yield df

def yeilder():
    i = 0
    while True:
        
        yield i
        i + i

    
#if __name__ == '__main__':
#    parser = argparse.ArgumentParser()
#    
#    parser.add_argument('ids_path', type=str, 
#                        help='Path to ids of interest')
#    parser.add_argument('field', type=str,
#                        help='Field in ids path. E.g. "SCENE_ID", "CATALOG_ID"')
#    parser.add_argument('out_path', type=str,
#                        help='Path to write shp of selection to.')
#    
#    args = parser.parse_args()
#    
#    
#
#    df = select_from_mfp(index_path, args.ids_path, args.field)
#    df.to_file(os.path.abspath(args.out_path), driver='ESRI_Shapefile')


    
