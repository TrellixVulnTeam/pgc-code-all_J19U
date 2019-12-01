# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 10:56:39 2019

@author: disbr007
Gets the offline drive names for a given input shapefile or text file.
"""

import argparse
import logging
import sys

import arcpy

from id_parse_utils import read_ids

sys.path.insert(0, r'C:\code\pgc-code-all\arcpy_utils')
from arcpy_utils import load_pgc_index


logger = logging.getLogger('get-src-drives')
formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(filename=r'E:\disbr007\scratch\fp_density.log', 
                    filemode='w', 
                    format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.DEBUG)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


def parse_input(ids_src):
    """
    Takes an input and determines if it is a .txt file of IDs or list of IDs.
    Returns an SQL formatted string for passing to a where_clause when
    loading an arcpy layer object.
    
    Parameters:
    ids_src (str or list): path to ids .txt file or list of ids
    
    Returns:
    str: SQL formatted string of IDs
    """
    try:
        if len(ids_src) == 1 and ids_src[0].endswith('.txt.'):
            ids = read_ids(ids_src[0])
        else:
            ids = ids_src

    except Exception as e:
        logger.info('''Cannot parse input ids source. 
            Please use a .txt or enter ids''')
        raise e
    
    ids_str = str(ids)[1:-1]
    
    return ids_str


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('ids_src', nargs='+',
                        help='Path to text file of IDs or IDs themselves.')
    parser.add_argument('--field', default='SCENE_ID',
                        help='Field of IDs entered: SCENE_ID or CATALOG_ID.')
    
    args = parser.parse_args()
    
    ids_src = args.ids_src
    field = args.field
    
    ids_str = parse_input(ids_src)
    selection = load_pgc_index(where="""{} IN ({})""".format(field, ids_str))
    

    scene_ids = []
    with arcpy.da.SearchCursor(selection, 'o_drive') as sc:
        for row in sc:
            scene_ids.append(row[0])
    scene_ids = set(scene_ids)
    
    logger.info("""Offline drives needed for selection:\n{}""".format('\n'.join(scene_ids)))
    
    with arcpy.da.SearchCursor(selection, 'o_filepath') as sc:
        for row in sc:
            print(row[0])