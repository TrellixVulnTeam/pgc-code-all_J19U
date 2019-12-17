# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 12:11:46 2019

@author: disbr007
"""

import argparse
import os
import logging

from id_parse_utils import read_ids, write_ids

# Args
ids_path = r'E:\disbr007\UserServicesRequests\Projects\bjones\1653\CatalogProducts_catalogids.txt' # Text file -- add support for comparing dirs
check_dir = r'V:\pgc\userftp\bmjones\4042_2019dec10\QB02\ortho'
write_path = r'V:\pgc\userftp\bmjones\4042_2019dec10\QB02\missing_from_ortho.txt'
write = True # Write included / not included IDs to text file
id_of_int = 'CATALOG_ID' # or CATALOG_ID, SCENE_ID


def imagery_directory_IDs(img_dir, id_of_int):
    """
    Parses the filenames of imagery in a given directory and returns a list of
    the specified ID type.
    
    Parameters:
    img_dir   (str) : path to directory of imagery
    id_of_int (str) : the type of ID to return, one of CATALOG_ID or SCENE_ID
    
    Returns:
    (set) : list of IDs
    """
    # STRING LITERALS
    CATALOG_ID = 'CATALOG_ID'
    SCENE_ID = 'SCENE_ID'
    PLATFORM = 'platform'
    PROD_CODE = 'prod_code'
    # PARSE IDS FROM CHECK DIR
    check_dir_parsed = {}
    for root, dirs, files in os.walk(check_dir):
        for f in files:
            # Parse filename
            scene_id = f.split('.')[0]
            first, prod_code, _third = scene_id.split('-')
            platform, _date, catalogid, _date_words = first.split('_')
            # Add to storage dict
            check_dir_parsed[f] = {}
    
            check_dir_parsed[f][CATALOG_ID] = catalogid
            check_dir_parsed[f][SCENE_ID] = scene_id
            check_dir_parsed[f][PROD_CODE] = prod_code
            check_dir_parsed[f][PLATFORM] = platform
    
    # Get ID of interest from check dir
    dir_ids = []
    for filename, f_dict in check_dir_parsed.items():
        dir_ids.append(f_dict[id_of_int])
    dir_ids = set(dir_ids)
    
    return dir_ids


def id_verify(source, compare2, id_of_int='CATALOG_ID', write_path=None, write=False):
    """
    Takes a source file or directory of IDs and compares them to either
    another file of IDs or a directory of imagery.
    
    Parameters:
    source     (str) : text, csv, dbf, etc. of ids, or a directory of imagery files
    compare2   (str) : same as source
    id_of_int  (str) : either CATALOG_ID or SCENE_ID - field to compare
    write_path (str) : optional path to write missing IDs to
    write      (bool): True to write missing IDs, otherwise just prints to console
    
    Returns
    (list) : missing ids
    """
    # LOGGING SETUP
    # Create logger
    logger = logging.getLogger('id_verify')
    logger.setLevel(logging.DEBUG)
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # Add the handler to the logger
    logger.addHandler(ch)
    
    # LOAD SOURCE IDS
    # Read in text file of IDs of interest (or shapfile, or CLI entry)
    source_ids = read_ids(source)
    source_ids = set(source_ids)
    logger.info("{}'s found in source: {}".format(id_of_int, len(source_ids)))
    

    compare2_ids = imagery_directory_IDs(compare2, id_of_int)
    logger.info("{}'s found in directory: {}".format(id_of_int, len(compare2_ids)))
    
    
    # COMPARE
    missing = source_ids - compare2_ids
#    common = source_ids.union(compare2_ids)
    logger.info("{} missing from directory: {} of {}".format(id_of_int, 
                                                             len(missing), 
                                                             len(source_ids)))
    
    # Write
    if write is True:
        if len(missing) == 0:
            logger.info('No missing IDs found, skipping writing.')
        logger.info('Writing {} missing IDs to {}'.format(len(missing),
                                                          write_path))
        write_ids(missing, write_path)

    return missing


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('source', type=str,
                        help='File of IDs (txt, csv, dbf) or directory of imagery')
    parser.add_argument('compare2', type=str,
                        help="""File of IDs (txt, csv, dbf) or directory of imagery 
                                to compare the source IDs to""")
    parser.add_argument('id_of_int', type=str, default='CATALOG_ID',
                        help='ID to compare, one of CATALOG_ID or SCENE ID')
    parser.add_argument('--write_path', type=str,
                        help="""Path to write missing IDs to. Optional, will
                                just print to console.""")
    
    args = parser.parse_args()
    
    source = args.source
    compare2 = args.compare2
    id_of_int = args.id_of_int
    write_path = args.write_path
    if write_path is not None:
        write = True
    else:
        write = False
    
    id_verify(source=source,
              compare2=compare2,
              id_of_int=id_of_int,
              write_path=write_path,
              write=write)
    
    
        