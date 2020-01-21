# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 17:39:33 2020

@author: disbr007
"""

import argparse
import os
import shutil
import tqdm

from id_parse_utils import parse_filename, read_ids
from logging_utils import create_logger


logger = create_logger(os.path.basename(__file__), 'sh')


def match_and_move(ids, src_dir, dst_dir, dryrun=False):
    logger.info('{} IDs found.'.format(len(ids)))
    matches = []
    catids_found = []
    logger.info('Locating matching files...')
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if 'BROWSE' not in f:
                catid = parse_filename(f, 'catalog_id')
                if catid in ids:
                    matches.append(os.path.join(root, f))
                    if catid not in catids_found:
                        catids_found.append(catid)
    
    logger.info('Matching imagery files found for {}/{} IDs.'.format(len(catids_found), len(ids)))
    logger.info('Moving matches to {}...'.format(dst_dir))
    for src in tqdm.tqdm(matches):
        if dryrun:
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
    parser.add_argument('--ids_field', type=str, default=None,
                        help='Field in shp or dbf src of IDs containing the IDs.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Read IDs and locate in src, but do not perform move.')
    
    args = parser.parse_args()
    
    ids_src = args.ids
    src_dir = args.src_dir
    dst_dir = args.dst_dir
    ids_field = args.ids_field
    
    ids = read_ids(ids_src, field=ids_field)
    
    match_and_move(ids, src_dir, dst_dir)
    
    