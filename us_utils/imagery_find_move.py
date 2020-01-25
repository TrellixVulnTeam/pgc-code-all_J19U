# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 17:39:33 2020

@author: disbr007
Finds imagery in a directory based on an input list of 
scene_ids or catalog_ids. Moves the imagery files to
destination directory.
***SKIPPING BROWSE FILES CURRENTLY***
TODO: Incorporate BROWSE files into parse_filename function
"""

import argparse
import os
import shutil
import tqdm

from id_parse_utils import parse_filename, read_ids, write_ids
from logging_utils import create_logger


logger = create_logger(os.path.basename(__file__), 'sh',
                       handler_level='INFO')


def match_and_move(ids, src_dir, dst_dir, match_field='catalog_id', dryrun=False):
    
    logger.info('{} IDs found.'.format(len(set(ids))))
    logger.debug(ids)
    matches = []
    catids_found = []
    logger.info('Locating matching files...')
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if 'BROWSE' not in f:
                catid = parse_filename(f, match_field)
                # logger.debug('{}: {}'.format(match_field, catid))
                if catid in ids:
                    matches.append(os.path.join(root, f))
                    if catid not in catids_found:
                        catids_found.append(catid)
    
    logger.info('Matching imagery files found for {}/{} IDs.'.format(len(catids_found), len(set(ids))))
    missing_ids = set(ids) - set(catids_found)
    logger.debug('Missing IDs: {}'.format(len(missing_ids)))
    # write_ids(missing_ids, r'C:\temp\akhan_missing_from_order.txt')
    logger.info('Moving matches to {}...'.format(dst_dir))
    for src in tqdm.tqdm(matches):
        if not dryrun:
            shutil.copyfile(src, os.path.join(dst_dir, os.path.basename(src)))
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('ids', type=os.path.abspath,
                        help="""Path to IDs. Can be text file of shp. If 
                                shp, defaults to catalogid field. If alternative
                                field desireed, provide field name of IDs.""")
    parser.add_argument('src_dir', type=os.path.abspath,
                        help="""Path to directory holding imagery to move.""")
    parser.add_argument('dst_dir', type=os.path.abspath,
                        help="""Path to directory to move imagery to.""")
    parser.add_argument('--match_field', type=str, default='catalog_id',
                        help='Field to match on. Usually one of catalog_id or scene_id.')
    parser.add_argument('--ids_field', type=str, default=None,
                        help='Field in shp or dbf src of IDs containing the IDs.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Read IDs and locate in src, but do not perform move.')
    
    args = parser.parse_args()
    
    ids_src = args.ids
    src_dir = args.src_dir
    dst_dir = args.dst_dir
    match_field = args.match_field
    ids_field = args.ids_field
    dryrun = args.dryrun
    
    ids = read_ids(ids_src, field=ids_field)
    
    match_and_move(ids, src_dir, dst_dir, match_field=match_field, dryrun=dryrun)
    
    