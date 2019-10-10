# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 22:39:54 2019

@author: disbr007
"""
import arcpy
from query_danco import query_footprint
import pandas as pd
import pickle
import os, sys
from id_parse_utils import pgc_index


wd = r'C:\Users\disbr007\projects\coastline'
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
src = 'nasa'

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
#    status = 'online' ## Change this to any status?
    cloudcover = 0.2
    sensors = ('WV02', 'WV03')
    prod_code = 'M1BS'
    abscalfact = 'NOT NULL'
    bandwith = 'NOT NULL'
    sun_elev = 'NOT NULL'
    max_ona = get_max_ona_ids()

    if src == 'mfp':
        where = f"""(cloudcover <= {cloudcover}) 
            AND (sensor IN {sensors})
            AND (prod_code = '{prod_code}')
            AND (abscalfact IS {abscalfact}) 
            AND (bandwidth IS {bandwith}) 
            AND (sun_elev IS {sun_elev})
            AND (catalog_id NOT IN {max_ona})"""
#           AND (status = {status})"""

    elif src == 'dg':
        where = f"""(cloudcover <= {int(cloudcover*100)})
            AND (platform IN {sensors})
            AND (catalogid NOT IN {max_ona})"""
    
    elif src == 'nasa':
        where = f"""(CLOUDCOVER <= {cloudcover}) 
            AND (SENSOR IN {sensors}) 
            AND (PROD_CODE = '{prod_code}')
            AND (ABSCALFACT IS {abscalfact}) 
            AND (BANDWIDTH IS {bandwith}) 
            AND (SUN_ELEV IS {sun_elev})
            AND (CATALOG_ID NOT IN {max_ona})"""
#            AND (status = {status})"""
            
    else:
        print('Unknown source for selection_clause(), must be one of "mfp" or "dg"')
        sys.exit()

    return where

#### Load src footprint, using coastline selection criteria
if src == 'mfp':
    # src_p = r'C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb\pgcImageryIndexV6_2019jun06'

    try:
        sys.path.insert(0, r'C:\pgc-code-all\misc_utils')
        from id_parse_utils import pgc_index_path
        src_p = pgc_index_path()
    except ImportError:
        src_p = r'C:\pgc_index\pgcImageryIndexV6_2019aug28.gdb\pgcImageryIndexV6_2019aug28'
        print('Could not load updated index. Using last known path: {}'.format(imagery_index))

elif src == 'dg':
   src_p = danco_footprint_connection('index_dg')
elif src == 'nasa':
    src_p = r'C:\pgc_index\nga_inventory_canon20190505\nga_inventory_canon20190505.gdb\nga_inventory_canon20190505'
    

#### Select by criteria
intermed_fc = 'memory\{}_intermed'.format(src)
where = selection_clause(src)
selection = arcpy.MakeFeatureLayer_management(src_p, os.path.join(gdb, intermed_fc), where_clause=where)
   