# -*- coding: utf-8 -*-
"""
Created on Sun Apr 19 13:24:58 2020

@author: disbr007
"""
import argparse
import os
import shutil

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

fp_p = r'V:\pgc\data\scratch\jeff\deliverables\akhan_temp\arc\arctic_footprints_32633.shp'
img_dir = r'V:\pgc\data\scratch\jeff\deliverables\akhan_temp\arc\raw'
dst_dir = r'V:\pgc\data\scratch\jeff\deliverables\akhan_temp\arc\raw_32608'
id_fld = 'SCENE_ID'
dryrun = False

def move_imagery_files(fp_p, src_dir, dst, dryrun):
    fp = gpd.read_file(fp_p)
    fp_sids = list(fp[id_fld])
    logger.info('IDs found in footprint: {}'.format(len(fp_sids)))
    
    move_files = []
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            f_sid = os.path.basename((f).split('.')[0])
            if f_sid in fp_sids:
                move_files.append(os.path.join(root, f))
    
    logger.info('Found {} files to move.'.format(len(move_files)))
    
    if not dryrun:
        logger.info('Moving files...')
        for src in tqdm(move_files):
            shutil.copyfile(src, os.path.join(dst_dir, os.path.basename(src)))
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-f', '--footprint', type=os.path.abspath,
                        help="""Path to the footprint containing a field of IDs to locate
                                imagery files by.""")
    parser.add_argument('-i', '--imagery_directory', type=os.path.abspath,
                        help="""Path to the directory containing imagery to move.""")
    parser.add_argument('-o', '--output_directory', type=os.path.abspath,
                        help="""Path to the directory to move imagery files to.""")
    parser.add_argument('-d', '--dryrun', action='store_true',
                        help='Locate files to move but do not move.')
    
    args = parser.parse_args()
    
    move_imagery_files(args.footprint,
                       args.imagery_directory,
                       args.output_directory,
                       args.dryrun)