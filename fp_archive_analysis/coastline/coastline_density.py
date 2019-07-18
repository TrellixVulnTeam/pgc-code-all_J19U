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
"""

import fiona, os, tqdm, logging
from pprint import pprint
import geopandas as gpd
import pandas as pd

from select_ids_pgc_index import mfp_subset
from archive_analysis_utils import get_count
from gpd_utils import merge_gdfs
from query_danco import query_footprint


## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

#lso = logging.StreamHandler()
#lso.setLevel(logging.INFO)
#lso.setFormatter(formatter)
#logger.addHandler(lso)


def get_max_ona_ids(where=None):
    '''
    Gets a list of those ids with the higher off nadir angle out of the stereopair
    where: SQL query to reduce load times if only specific records are needed. E.g. "platform in ('WV02', 'WV03')"
    '''
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
    
    return list(max_ona_ids)


## Set up paths
wd = r"C:\Users\disbr007\projects\coastline\scratch"
coast_n = 'greenland_coast_10km.shp'
geocells_p = r"E:\disbr007\general\geocell\Global_GeoCell_Coverage.shp"

## Read in coastline
noaa_coast_p = os.path.join(wd, coast_n)
coast = gpd.read_file(noaa_coast_p, driver='ESRI Shapefile')
geocells = gpd.read_file(geocells_p, driver='ESRI Shapefile')

# Dissolve coast to simplify, then buffer 10km - projection is in meters
coast['dis'] = 0
coast = coast.dissolve(by='dis')
#coast['geometry'] = coast['geometry'].buffer(10E3)

# Perform spatial join to select only geocells that intersect with coastline, keep only original goecells columns
if coast.crs != geocells.crs:
    coast.to_crs(geocells.crs, inplace=True)
geocells_cst = gpd.sjoin(geocells, coast, how='left', op='intersects')[list(geocells)]
# Create column to store counts of density
geocells_cst['count'] = 0
gc_cols = list(geocells_cst)


## Read in masterfootprint subsets - only those within given latitude and longitude and loop over mfp subsets
# Store matches from each subset in a list of geodataframes
all_matches = []
logging.info('Applying further selection criteria (status, cc, sensor, prod_code, etc.) and performing sjoin.')

# Get all ids that were the higher of the pair's ONA
max_ona_ids = get_max_ona_ids(where="platform in ('WV02', 'WV03')")

for layer in tqdm.tqdm(mfp_subset(-60, 60, 0, 90)):
    selection = layer[(layer['status'] == 'online') &
                      (layer['cloudcover'] <= 0.2) &
                      (layer['sensor'].isin(['WV02', 'WV03'])) &
                      (layer['prod_code'] == 'M1BS') &
                      (layer['abscalfact'] != None) &
                      (layer['bandwidth'] != None) &
                      (layer['sun_elev'] != None)]
    

    # Remove higher ONA's
    selection = selection[~selection['catalog_id'].isin(max_ona_ids)]
    
    # Confirm same coordinate system for coastline and mfp
    if coast.crs != layer.crs:
        coast.to_crs(layer.crs, inplace=True)
        
    # Get count of features in each geocell 
    counted = get_count(geocells_cst, layer)
    
        

## Place all matches into intermediate geodataframe for further selection and reduction
init_selection = merge_gdfs(all_matches)







