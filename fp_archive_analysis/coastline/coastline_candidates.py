# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 11:51:05 2019

@author: disbr007
Selects footprints from the master footprint that meet the following criteria:
    -w/in 10km of the provided coastline shapefile
    -are online
    -have cc20 or better
    -WV02 or WV03
    -prod code M1BS (multispectral)
    -abscalfact not None
    -bandwith not None
    -sun elev not None
    -lower off nadir angle
"""
import arcpy

import os, logging
import geopandas as gpd
import pandas as pd
import pickle
#from shapely.ops import nearest_points
from tqdm import tqdm

from select_ids_pgc_index import mfp_subset
from query_danco import query_footprint


## Set up logging
formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

## Set up paths
wd = r'C:\Users\disbr007\projects\coastline'
#coast_n = r'coastline_shp\GSHHS_f_L1_GIMPgl_ADDant_USGSgl_pline_55N_arctic_polar_dis_.shp'
coast_n = r'scratch\greenland_coast.shp'


def get_max_ona_ids(update=False, where=None, wd=wd):
    '''
    Gets a list of those ids with the higher off nadir angle out of the stereopair
    where: SQL query to reduce load times if only specific records are needed. E.g. "platform in ('WV02', 'WV03')"
    '''
    if update:
#        logging.INFO("Compiling list of the higher off-nadir-angle IDs...")
        print("Compiling list of the higher off-nadir-angle IDs...")
        
        # Load min ona footprint
        min_ona = query_footprint(layer='dg_stereo_catalogids_having_min_ona',
                                  columns=['catalogid'],
                                  where=where)
        # Load all stereo footprint with stereopair column
        all_str = query_footprint(layer='dg_imagery_index_stereo_onhand_cc20',
                                  columns=['catalogid', 'stereopair'],
                                  where=where)
        
        # Finds only min_ona ids listed as 'catalogid' in stereo footprint
        min_ona_pairs1 = pd.merge(min_ona, all_str, on='catalogid', how='inner')
        max_ona_ids1 = min_ona_pairs1['stereopair']
        
        # Finds only min_ona ids listed as 'stereopair' in stereo footprint
        min_ona_pairs2 = pd.merge(min_ona, all_str, left_on='catalogid', right_on='stereopair', suffixes=('_l', '_r'))
        max_ona_ids2 = min_ona_pairs2['catalogid_r']
        
        # Add two lists together, return unique ids (they all should be...) as a list
        max_ona_ids = pd.concat([max_ona_ids1, max_ona_ids2])
        max_ona_ids = max_ona_ids.unique()
        max_ona_ids = list(max_ona_ids)
        
        with open(os.path.join(wd, 'pickles', 'max_ona_ids.pkl'), 'wb') as pkl:
            pickle.dump(max_ona_ids, pkl)
    
    else:
        with open(os.path.join(wd, 'pickles', 'max_ona_ids.pkl'), 'wb') as pkl:
            max_ona_ids = pickle.load(pkl)
    
    return max_ona_ids


def nearest_distance(geom1, geom2):
    '''
    Finds the nearest distance between two shapely geometries.
    geom1 + geom2: shapely geometries
    '''
    # Find the nearest points - returns a list [np on geom1, np on geom2]
    np = nearest_points(geom1, geom2)
    dist = np[0].distance(np[1])
    
    return dist


## Read in coastline
logging.info('Loading coast...')
noaa_coast_p = os.path.join(wd, coast_n)
coast = gpd.read_file(noaa_coast_p, driver='ESRI Shapefile')


## Prepare coastline
# Dissolve coast to simplify
logging.info('Dissolving coast...')
coast['dis'] = 0
coast = coast.dissolve(by='dis')
#coast.drop(columns='dis')

# Simplify coast geometry
#coast['simp_geom'] = coast.geometry
#coast['simp_geom'][0] = coast['simp_geom'][0].simplify(500, preserve_topology=False)

# Buffer 10km - assuming projection is in meters
#logging.info('Buffering coastline 10km...')
#coast['geometry'] = coast['geometry'].buffer(10E3)


## Read in masterfootprint subsets - only those within given latitude and longitude and loop over mfp subsets
# Store matches from each subset in a list of geodataframes
all_matches = []
logging.info('Applying further selection criteria (status, cc, sensor, prod_code, etc.) and performing sjoin.')

# Get all ids that were the higher of the pair's ONA
max_ona_ids = get_max_ona_ids(update=True, where="platform in ('WV02', 'WV03')")

for layer in mfp_subset(-85, 55, -5, 90):
    print('Working on layer of {} features.'.format(len(layer)))
    logging.info('Working on layer of {} features.'.format(len(layer)))
    selection = layer[(layer['status'] == 'online') &
                      (layer['cloudcover'] <= 0.2) &
                      (layer['sensor'].isin(['WV02', 'WV03'])) &
                      (layer['prod_code'] == 'M1BS') &
                      (layer['abscalfact'] != None) &
                      (layer['bandwidth'] != None) &
                      (layer['sun_elev'] != None)]
    

    # Remove higher ONA's
    selection = selection[~selection['catalog_id'].isin(max_ona_ids)]
    
    # Confirm same coordinate system for coastline and mfp, if not reproject coastline
    if layer.crs != coast.crs:
        logging.info('Reprojecting master footprint subset...')
        layer.to_crs(coast.crs, inplace=True)
    
    # Perform spatial join (intersect), keeping footprint geometries
#    selection = gpd.sjoin(selection, coast, how='inner')
    ## This method requires dissolving the coastline so there is only one feature in it
    selection['distance'] = selection.progress_apply(lambda x: nearest_distance(x['geometry'].centroid, coast['geometry'][0]), axis=1)
    selection = selection[selection['distance'] <= 1000.0]

    all_matches.append(selection)


## Merge all matches into intermediate geodataframe for further selection and reduction
init_selection = gdf = gpd.GeoDataFrame(pd.concat(all_matches, ignore_index=True), crs=all_matches[0].crs)
init_selection.to_pickle(os.path.join(wd, 'scratch\greenland_test.pkl'))
