# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:20:30 2020

@author: disbr007
"""
# jclark file mover
import argparse
import os
import shutil

import geopandas as gpd

from id_parse_utils import parse_filename
from logging_utils import create_logger


logger = create_logger('file_mover', 'sh',
                       'DEBUG')


# prj_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark'
# raw_dir = os.path.join(prj_dir, 'raw')
# dst_dir = os.path.join(prj_dir, 'ortho')

# lut_p = os.path.join(prj_dir, 'IDs_buffers_master.shp')
# dryrun = True

def file_mover(lut_shp, src_dir, dst_dir,
               lut_sd, lut_id,
               dryrun):
        
    # Read in LUT shapefile
    lut = gpd.read_file(lut_shp)
    
    # Walk src directory
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if f.endswith(('tif', 'ntf')):
                src_fp = os.path.join(root, f)
                # Get catalogid from filename
                f_id = parse_filename(f, lut_id, fullpath=False)
                # Look up catalogid in LUT shapefile to get destination subdirectory
                # allowing for multiple matches
                dst = list(lut[lut.ID == f_id][lut_sd].unique())
                # For every destination
                for d in dst:
                    dst_subdir = os.path.join(dst_dir, d)
                    # If subdirectory does not exist, create it
                    if not os.path.exists(dst_subdir):
                        os.makedirs(dst_subdir)
                    # Full destination filepath
                    dst_fp = os.path.join(dst_subdir, f)
                    if not os.path.exists(dst_fp):
                        logger.info('Copying {} to: {}'.format(f, d))
                        # Copy file to subdirectory
                        if not dryrun:
                            shutil.copy2(src_fp, dst_fp)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('src', type=os.path.abs_path,
                        help='Path to directory containing imagery to be moved/copied.')
    parser.add_argument('dst', type=os.path.abspath,
                        help='Path to destination directory to create subdirectories in.')
    parser.add_argument('look_up', type=os.path.abspath,
                        help='Path to shapefile to use as look-up table.')
    parser.add_argument('look_up_subdir', type=str,
                        help='Field name in look-up to use for subdirectories.')
    parser.add_argument('look_up_id', type=str,
                        help="""Field name in look-up to use for IDs. One of:
                                'catalog_id', 'scene_id', 'platform'""")
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')
                                
    args = parser.parse_args()
    
    src = args.src
    dst = args.dst
    look_up = args.look_up
    look_up_subdir = args.look_up_subdir
    look_up_id = args.look_up_id
    dryrun = args.dryrun
    
    file_mover(look_up, src_dir=src, dst_dir=dst, 
               lut_sd=look_up_subdir, lut_id=look_up_id, dryrun=dryrun)
    
    