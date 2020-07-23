# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 11:07:11 2020

@author: disbr007
"""
import argparse
import os

import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import type_parser, read_ids, write_ids


logger = create_logger(__name__, 'sh', 'DEBUG')

# src = r'V:\pgc\data\scratch\jeff\deliverables\4218_schild_thwaites_dems\schild_2020jun03_request_init_selection.shp'
# oth = r'V:\pgc\data\scratch\jeff\deliverables\4129_schild_thwaites_dems\4129_2020feb26_thwaties_dems.txt'
# out_path = r'V:\pgc\data\scratch\jeff\deliverables\4218_schild_thwaites_dems\schild_2020jun03_request_init_selection_cleaned.shp'
# src_field = 'pairname'
# oth_field = None


def remove_ids(src, oth, out_path=None, src_field=None, oth_field=None):
    logger.info('\nRemoving IDs in: {}\nFrom:            {}'.format(oth, src))
    
    # Determine input types
    src_type = type_parser(src)
    oth_type = type_parser(oth)
    
    logger.debug('Source file type: {}'.format(src_type))
    logger.debug('Other file type: {}'.format(oth_type))
    
    # Read in IDs
    src_ids = read_ids(src, field=src_field)
    oth_ids = read_ids(oth, field=oth_field)
    
    logger.info('Source IDs: {:,}'.format(len(src_ids)))
    if len(src_ids) != len(list(set(src_ids))):
        logger.info('Unique source IDs: {:,}'.format(len(list(set(src_ids)))))
    
    logger.info('Other IDs: {:,}'.format(len(oth_ids)))
    if len(oth_ids) != len(list(set(oth_ids))):
        logger.info('Unique source IDs: {:,}'.format(len(list(set(oth_ids)))))
    
    
    # Remove IDs in other from source
    rem_ids = set(src_ids) - set(oth_ids)
    ids_removed = len(src_ids) - len(rem_ids)
    logger.info('IDs removed: {:,}'.format(ids_removed))
    
    # Write source out without other IDs
    if ids_removed != 0:
        if src_type == 'shp' or src_type == 'df':
            out = gpd.read_file(src)
            out = out[out[src_field].isin(rem_ids)]
            if src_type == 'shp':
                out.to_file(out_path)
        elif src_type == 'id_only_txt':
            out = rem_ids
            write_ids(out, out_path)
        else:
            logger.error('Source type not supported: {}'.format(src_type))
    else:
        logger.warning('No IDs removed from source.')
        out = None
        
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-s', '--source_ids', type=os.path.abspath,
                        help='Path to source IDs to remove from.')
    parser.add_argument('-r', '--remove_ids', type=os.path.abspath,
                        help='Path to IDs to remove.')
    parser.add_argument('-o', '--out_ids', type=os.path.abspath,
                        help='Path to write cleaned IDs to.')
    parser.add_argument('-sf', '--source_field', type=str,
                        help='The field in source to pull from, if not text file.')
    parser.add_argument('-rf', '--remove_field', type=str,
                        help='The field in remove_ids to pull from, if not text file.')
    
    args = parser.parse_args()
    
    remove_ids(src=args.source_ids, oth=args.remove_ids,
               out_path=args.out_ids, src_field=args.source_field,
               oth_field=args.remove_field)
    