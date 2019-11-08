# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 09:51:50 2019

@author: disbr007

Uploads from drives to server.
"""

import argparse
import datetime
import logging
import posixpath
import os
import sys
import shutil

import pandas as pd
import geopandas as gpd
from tqdm import tqdm
#from tqdm.auto import tqdm

from query_danco import query_footprint


def all_ahap_drives():
    """
    Lists all offline drives with AHAP imagery
    """
    aia = query_footprint('usgs_index_aerial_image_archive', 
                      db='imagery', 
                      table=True, 
                      where="campaign = 'AHAP'")
    src_drives = aia.src_drive.unique()
    
    return src_drives
    

def get_drives():
    """
    List all active drives.
    """
    drive_list = []
    for drive in range(ord('A'), ord('N')):
        if os.path.exists(chr(drive) + ':'):
            drive_list.append(chr(drive) + ':')
    return drive_list


def det_res_dir(series):
    """
    Determine subdir name based on series
    """
    if series == 'medium_res':
        res_dir = 'med'
    elif series == 'high_res':
        res_dir = 'high'
    else:
        res_dir = 'unk'
    
    return res_dir


def det_server_path(row):
    """
    Create server path for each row
    """
    roll_dir = os.path.split(os.path.dirname(row['filepath']))[1]
    server_path = os.path.join(row['res_dir'], roll_dir, row['filename'])
    
    return server_path


def main(parse_drives, server_loc, log, verbose, dryrun):
    """
    Uploads imagery from drives to server
    server_loc:    destination directory for imagery
    log       :    log file destination
    verbose   :    True to print logger.DEBUG messages
    dryrun    :    True to print actions without running
    """
    #### Logging setup
    # create logger
    logger = logging.getLogger('ahap_upload')
    logger.setLevel(logging.DEBUG)
    # create file handler
    fh = logging.FileHandler(log)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    if verbose:
        ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.debug('Log file created at: {}'.format(log))

    #### Determine which letter drives are imagery drives
    if not parse_drives:
        ## All active drives
        drives = get_drives()
        ## Check if drive is AHAP
        # TODO: fix this - not correct logic/path for high res
        ahap_drives = [os.path.join(d, 'AHAP Tif files') for d in drives if os.path.exists(os.path.join(d, 'AHAP Tif files'))]
    else:
        ahap_drives = [os.path.join(d, 'AHAP Tif files') for d in parse_drives if os.path.exists(os.path.join(d, 'AHAP Tif files'))]
        if len(parse_drives) != len(ahap_drives):
            logger.warning("""All provided drives did not match AHAP drive structure. ('D:\AHAP Tif files\...')
                           Matching drives: {}""".format([x[:2] for x in ahap_drives]))
        
    if len(ahap_drives) == 0:
        logger.info('No AHAP drives found. Exiting...')
        sys.exit()
    logger.info('AHAP Drives: {}'.format([x[:2] for x in ahap_drives]))
    
    
    #### Get paths to imagery on drives
    logger.info('Parsing drives...')
    drive_assoc = []
    drive_paths = []
    drive_fnames = []
    image_ids = []
    for d in ahap_drives:
        for root, dirs, files in os.walk(d):
            for f in files:
                drive_assoc.append(d)
                image_path = os.path.join(root, f)
                # TODO: Maybe check here if filename starts with 58 or 59 to determine AHAP or not?
                drive_paths.append(image_path)
                drive_fnames.append(f)
                image_id = f.split('.')[0]
                image_ids.append(image_id)
    
    ## Create dataframe of: drive - drive path - drive filename - image id
    drives_df = pd.DataFrame({'drive':drive_assoc, 
                              'drive_path':drive_paths, 
                              'drive_fname':drive_fnames, 
                              'image_id':image_ids}) 
    
    
    #### Convert to server paths
    ## Determine high or low res based on filename (compressed or not) in table
    # Load table
    aia = query_footprint('usgs_index_aerial_image_archive', 
                          db='imagery', 
                          table=True, 
                          where="campaign = 'AHAP'")
    # Join on filenames (compressed or not)
    drives_df = drives_df.merge(aia, how='inner',
                                left_on='drive_fname', right_on='filename')
    # Create resolution sub directory name ('med' or 'high') based on 'series' in table
    drives_df['res_dir'] = drives_df['series'].apply(lambda x: det_res_dir(x))
    
    # Convert unix style path to os style (i.e. windows)
    drives_df['filepath'] = drives_df['filepath'].str.replace(posixpath.sep, os.sep)
    # Create server path for each image (where it would be if it existed or where it should go)
    # TODO: make this nicer
    drives_df['server_path'] = (server_loc + 
                                os.path.sep + 
                                drives_df.apply(lambda x: det_server_path(x), axis=1)) # Nicer way?
    
    
    #### Check for existence on server
    ## TODO: speed this up - bottleneck
    logger.info('Checking for existence of drive imagery on server...')
    drives_df['online'] = drives_df['server_path'].apply(lambda x: os.path.exists(x))
    offline = drives_df[drives_df['online']==False]
    logger.info('Image files on drives not on server: {}'.format(len(offline)))
    
    
    #### Copy missing paths to server
    for letter_drive in offline['drive'].unique():
        offline_count = len(offline[offline['drive']==letter_drive])
        usgs_drive = offline['src_drive'].unique()[0]
        logger.debug('Image files on drive {} not on server: {}'.format(letter_drive[:2], 
                                                                  offline_count))
        logger.info('Transfering from drive: {} -- {}'.format(letter_drive[:2], usgs_drive))
        for src, dst in tqdm(zip(offline[offline['drive']==letter_drive]['drive_path'], 
                                 offline[offline['drive']==letter_drive]['server_path']),
                             total=offline_count):
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                logger.debug('Making directories: {}'.format(dst_dir))
                if not dryrun:
                    os.makedirs(dst_dir)
            if not dryrun:
                shutil.copyfile(src, dst)
            logger.debug('Copied {} \n to {}'.format(src, dst))
            # TODO os.stat to confirm transfer?
        logger.info('Completed transferring: {}'.format(letter_drive[:2]))
        if not dryrun:
            with open(r'C:\code\pgc-code-all\ahap_utils\ahap_copier.py', 'a') as master_log:
                master_log.write(usgs_drive)
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('--drives', nargs='+',
                        help='Letters of drives to parse and copy.')
    parser.add_argument('-d', '--destination', type=str, 
                        default=r'V:\pgc\data\aerial\usgs\ahap\photos',
                        help='Destination directory. Resolution folders will start here.')
    parser.add_argument('-l', '--log', type=str,
                        help='Log file location. Default to cwd.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set console logger level to DEBUG.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without running.')
    parser.add_argument('--list_src_drives', action='store_true',
                        help='Print all src_drives and exit.')
    
    args = parser.parse_args()
    
    parse_drives = args.drives
    server_loc = args.destination
    log = args.log
    verbose = args.verbose
    dryrun = args.dryrun
    list_src_drives = args.list_src_drives
    
    if log is None:
        now = datetime.datetime.now().strftime('%Y%b%d_%H%M%S').lower()
        log_name = 'ahap_transfer_{}.log'.format(now)
        log = os.path.join(os.getcwd(), log_name)
    
    if list_src_drives:
        src_drives = all_ahap_drives()
        for sd in src_drives:
            print(sd)
        sys.exit()
        
    main(parse_drives=parse_drives, server_loc=server_loc, log=log, verbose=verbose, dryrun=dryrun)
