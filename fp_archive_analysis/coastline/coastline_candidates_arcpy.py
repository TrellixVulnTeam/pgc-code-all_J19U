# -*- coding: utf-8 -*-
"""
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

import os, logging, sys, pickle
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

from query_danco import query_footprint


#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


#### Paths to source data
wd = r'C:\Users\disbr007\projects\coastline'
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
#coast_n = 'greenland_coast'
coast_n = 'GSHHS_f_L1_GIMPgl_ADDant_USGSgl_pline'


#### Output feature class name + arcpy env
arcpy.env.workspace = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
arcpy.env.overwriteOutput = True
out_name = 'global_coastline_candidates'


def get_max_ona_ids(update=False, where=None, wd=wd):
    '''
    Gets a list of those ids with the higher off nadir angle out of the stereopair
    where: SQL query to reduce load times if only specific records are needed. E.g. "platform in ('WV02', 'WV03')"
    '''
    if update:
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
        with open(os.path.join(wd, 'pickles', 'max_ona_ids.pkl'), 'rb') as pkl:
            max_ona_ids = pickle.load(pkl)
    
    return max_ona_ids


#### Get all ids that were the higher of the pair's ONA
logger.info('Getting max off-nadir angle IDs to remove from selection.')
max_ona_ids = get_max_ona_ids(update=False, where="platform in ('WV02', 'WV03')")


#### Load coastline
logger.info('Loading coastline.')
noaa_coast_p = os.path.join(gdb, coast_n)
#coast = arcpy.MakeFeatureLayer_management(noaa_coast_p)


#### Load master footprint, using coastline selection criteria
logger.info('Loading master footprint.')
mfp_p = r'C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb\pgcImageryIndexV6_2019jun06'


#### Select only footprints that are within 10 km of coastline
logging.info('Identifying footprints within 10 kilometers of coastline.')
selection = arcpy.SelectLayerByLocation_management(mfp_p, 
                                                   overlap_type='INTERSECT',
                                                   select_features=noaa_coast_p,
                                                   search_distance='10 Kilometers',
                                                   selection_type='NEW_SELECTION')

logging.info('Copying intermediate selection...')
selection = arcpy.CopyFeatures_management(selection, 'intermed_sel')
del selection

logging.info('Selecting based on criteria.')
where = """(status = 'online') 
            AND (cloudcover <= 0.2) 
            AND (sensor IN ('WV02', 'WV03')) 
            AND (prod_code = 'M1BS')
            AND (abscalfact IS NOT NULL) 
            AND (bandwidth IS NOT NULL) 
            AND (sun_elev IS NOT NULL)
            AND (catalog_id NOT IN {})""".format(tuple(max_ona_ids))


selection = arcpy.MakeFeatureLayer_management('intermed_sel', where_clause=where)

##### Write to new feature class
logging.info('Writing candidates to feature class.')
final_selection = arcpy.CopyFeatures_management(selection, out_feature_class=out_name)


logging.info('Done.')
