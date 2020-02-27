# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 12:11:46 2019

@author: disbr007
"""

import argparse
import os
import sys

from misc_utils.id_parse_utils import read_ids, write_ids, parse_filename
from misc_utils.logging_utils import create_logger


logger = create_logger('id_verify.py', 'sh')


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
    # PARSE IDS FROM IMG_DIR
    dir_ids = []
    for root, dirs, files in os.walk(img_dir):
        for f in files:
            if f.endswith(('tif', 'ntf')):
               img_id_of_int = parse_filename(f, id_of_int) 
               dir_ids.append(img_id_of_int)
    # Keep only unique
    dir_ids = set(dir_ids)
    
    return dir_ids


def get_ids(source, id_of_int, field=None, source_write=None):
    """
    Takes a 'source' that is either a directory or file and returns the IDs from that source.
    
    Parameters:
    -------
    source : os.path.abspath
        Either a file or directory path
    id_of_int : STR
        Type of ID to parse source for, one of: CATALOG_ID or SCENE_ID usually
    field : STR
        If source is a shp, dbf, etc, the field name to pull IDs from
    
    Returns:
    -------
    ids : LIST
        
    """
    # Determine type of source (file or directory)
    if os.path.isdir(source):
        source_ids = imagery_directory_IDs(source, id_of_int)
    elif os.path.isfile(source):
        if field is None:
            field = id_of_int
        # Read in text file of IDs of interest (or shapfile, or CLI entry)
        source_ids = read_ids(source, field=field)
        source_ids = set(source_ids)
    else:
        logger.warning('Unknown source type for: {}'.format(source))
        source_ids = None
    if source_write is not None:
        logger.info('Writing IDs to: {}'.format(source_write))
        write_ids(source_ids, source_write)
    
    return source_ids


def id_verify(source, id_of_int, compare2=None, 
              source_field=None, compare2_field=None,
              source_write=None, compare2_write=None,
              write_path=None, write=False):
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
    logger.info(id_of_int)
    # LOAD SOURCE IDS
    source_ids = get_ids(source, id_of_int, field=source_field, source_write=source_write)
    logger.info("{}'s found in source: {}".format(id_of_int, len(source_ids)))
    

    # LOAD compare2 ids
    compare2_ids = get_ids(source, id_of_int, field=compare2_field, compare2_write=compare2_write)
    logger.info("{}'s found in directory: {}".format(id_of_int, len(compare2_ids)))
    
    
    # COMPARE
    missing = source_ids - compare2_ids
#    common = source_ids.union(compare2_ids)
    logger.info("{} missing from directory: {} of {}".format(id_of_int, 
                                                             len(missing), 
                                                             len(source_ids)))
    
    # WRITE
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
    parser.add_argument('id_of_int', type=str, default='CATALOG_ID',
                        help='ID to compare, one of CATALOG_ID or SCENE ID')
    parser.add_argument('--compare2', type=str, default=None,
                        help="""File of IDs (txt, csv, dbf) or directory of imagery 
                                to compare the source IDs to""")
    parser.add_argument('--source_field', type=str,
                        help='Field in source to pull IDs from, if source is file (.shp, .dbf, etc.')
    parser.add_argument('--compare2_field', type=str,
                        help='Field in compare2 to pull IDS from, if compare2 is file (.shp, .dbf, etc.')
    parser.add_argument('--source_write', type=os.path.abspath,
                        help='Path to write source IDs to.')
    parser.add_argument('--compare2_write', type=os.path.abspath,
                        help='Path to write compare2 IDs to.')
    parser.add_argument('--write_path', type=str,
                        help="""Path to write missing IDs to. Optional, will
                                just print to console if flag not provided.""")

    # Parse args
    args = parser.parse_args()
    
    source = args.source
    id_of_int = args.id_of_int
    compare2 = args.compare2
    source_field = args.source_field
    compare2_field = args.source_field
    source_write = args.source_write
    compare2_write=args.compare2_write
    write_path = args.write_path
    
    
    if write_path is not None:
        write = True
    else:
        write = False
    
    
    if compare2 is None:
        source_ids = get_ids(source, id_of_int, field=source_field, source_write=source_write)
        logger.info('Source IDs found: {}'.format(len(source_ids)))
    
    else:
        id_verify(source=source,
                  compare2=compare2,
                  id_of_int=id_of_int,
                  source_field=source_field,
                  compare2_field=compare2_field,
                  source_write=source_write,
                  compare2_write=compare2_write,
                  write_path=write_path,
                  write=write)
