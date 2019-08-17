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
coast_n = 'GSHHS_f_L1_GIMPgl_ADDant_USGSgl_pline'


## Type of candidates - from dg footprint ('dg') or masterfootprint ('mfp')
src = 'dg'

#### Search distance
distance = 10


#### Output feature class name + arcpy env
arcpy.env.workspace = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
arcpy.env.overwriteOutput = True
out_name = 'dg_global_coastline_candidates'


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
    
    return tuple(max_ona_ids)


def selection_clause(src):
    '''
    Returns the selection criteria for a given source, master footprint or dg footprint
    src: str 'mfp' or 'dg'
    '''
    #### Selection criteria
    status = 'online'
    cloudcover = 0.2
    sensors = ('WV02', 'WV03')
    prod_code = 'M1BS'
    abscalfact = 'NOT NULL'
    bandwith = 'NOT NULL'
    sun_elev = 'NOT NULL'
    max_ona = get_max_ona_ids()

    if src == 'mfp':
        where = f"""(status = {status}) 
            AND (cloudcover <= {cloudcover}) 
            AND (sensor IN {sensors}) 
            AND (prod_code = {prod_code})
            AND (abscalfact IS {abscalfact}) 
            AND (bandwidth IS {bandwith}) 
            AND (sun_elev IS {sun_elev})
            AND (catalog_id NOT IN {max_ona})"""

    elif src == 'dg':
        where = f"""(cloudcover <= {int(cloudcover*100)})
            AND platform IN {sensors}
            AND catalogid NOT IN {max_ona}"""
            
    else:
        print('Unknown source for selection_clause(), must be one of "mfp" or "dg"')
        sys.exit()

    return where


#def danco_footprint_connection():
#    creds = []
#    with open(r"C:\code\pgc-code-all\cred.txt", 'r') as cred:
#        content = cred.readlines()
#        for line in content:
#            creds.append(str(line).strip())
#    
#    
#    out_folder_path = r'C:\dbconn\arcpy_cxn'
#    out_name = r'footprint_arcpy.sde'
#    database_platform = 'POSTGRESQL'
#    instance = r'danco.pgc.umn.edu'
#    account_authentication= 'DATABASE_AUTH'
#    database = 'footprint'
#    schema = ''
#    username = creds[0]
#    password = creds[1]
#    save_user_pass = "DO_NOT_SAVE_USERNAME"
#    version_type = 'TRANSACTIONAL'
#    version = 'sde.DEFAULT'
#    date = ''
#    
#    
#    
#    arcpy.env.overwriteOutput = True
#    
#    cxn = arcpy.CreateDatabaseConnection_management(out_folder_path=out_folder_path,
#                                              out_name=out_name,
#                                              database_platform=database_platform,
#                                              instance=instance,
#                                              account_authentication=account_authentication,
#                                              username=username,
#                                              password=password,
#                                              save_user_pass=save_user_pass,
#                                              database=database,
#                                              schema=schema,
#                                              version_type=version_type,
#                                              version=version,
#                                              date=date)
#    
#    print(f'Connected to {instance}: {database}.')
#    
#    return os.path.join(out_folder_path, 'footprint.sde.index.dg')
    
def danco_footprint_connection(layer):
    arcpy.env.overwriteOutput = True

    # Local variables:
    arcpy_cxn = "C:\\dbconn\\arcpy_cxn"
    #arcpy_footprint_MB_sde = arcpy_cxn
    
    # Process: Create Database Connection
    cxn = arcpy.CreateDatabaseConnection_management(arcpy_cxn, 
                                                     "footprint_arcpy.sde", 
                                                     "POSTGRESQL", 
                                                     "danco.pgc.umn.edu", 
                                                     "DATABASE_AUTH", 
                                                     "disbr007", 
                                                     "ArsenalFC10", 
                                                     "SAVE_USERNAME", 
                                                     "footprint", 
                                                     "", 
                                                     "TRANSACTIONAL", 
                                                     "sde.DEFAULT", 
                                                     "")
    
    arcpy.env.workspace = os.path.join("C:\\dbconn\\arcpy_cxn", "footprint_arcpy.sde")
    
    return '{}.sde.{}'.format('footprint', layer)



#### Load coastline
logger.info('Loading coastline.')
noaa_coast_p = os.path.join(gdb, coast_n)


#### Load src footprint, using coastline selection criteria
logger.info('Loading source footprint.')
if src == 'mfp':
    src_p = r'C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb\pgcImageryIndexV6_2019jun06'
    
elif src == 'dg':
    src_p = danco_footprint_connection('index_dg')
    

#### Select by criteria
logger.info('Selecting based on criteria.')
selection = arcpy.MakeFeatureLayer_management(src_p, os.path.join(gdb, 'intermed_sel'), where_clause=selection_clause(src))
logging.info('Features selected: {}'.format(arcpy.GetCount_management(selection)))

logger.info('Writing intermediate selection...')
selection = arcpy.CopyFeatures_management(selection, os.path.join(gdb, 'intermed_sel'))


#### Select only footprints that are within 10 km of coastline
logger.info('Identifying footprints within 10 kilometers of coastline.')
selection = arcpy.SelectLayerByLocation_management(os.path.join(gdb, 'intermed_sel'), 
                                                   overlap_type='INTERSECT',
                                                   select_features=noaa_coast_p,
                                                   search_distance=f'{distance} Kilometers',
                                                   selection_type='NEW_SELECTION')
logging.info('Features selected: {}'.format(arcpy.GetCount_management(selection)))

##### Write to new feature class
logger.info('Writing final candidates to feature class.')
final_selection = arcpy.CopyFeatures_management(selection, out_feature_class=os.path.join(gdb, out_name))
logging.info('Features selected: {}'.format(arcpy.GetCount_management(selection)))

logger.info('Done.')

