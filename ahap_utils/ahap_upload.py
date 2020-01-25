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
import subprocess

import numpy as np
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
#from tqdm.auto import tqdm

from query_danco import query_footprint
from logging_utils import create_logger


# # # INPUTS
# server_loc = r'V:\pgc\data\aerial\usgs\ahap\photos'
# dryrun = True
# list_src_drives = False
# verbose = True
# prj_dir = r'C:\ahap_upload'
# drives = 'D'

logger = create_logger('ahap_upload.py', 'sh')

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
    

def get_active_drives():
    """
    List all active drives.
    """
    drive_list = []
    for drive in range(ord('A'), ord('Z')):
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
    roll_dir = 'AB{}ROLL'.format(row['filename'][:-8])
    server_path = os.path.join(row['res_dir'], roll_dir, row['filename'])
    
    return server_path


def ahap_upload(server_loc, prj_dir, drives=None, skip_log=False, drive_loc=None,
                dryrun=False, verbose=False):
    """
    Upload imagery from mounted drives to server location based on 
    filepath in danco table 'usgs_index_aerial_image_archive'

    Parameters
    ----------
    server_loc : os.path.abspath
        Path to upload to.
    prj_dir : os.path.abspath
        Directory to write logs to.
    drives : LIST
        Drive letters to search.
    skip_log : BOOLEAN
        Skip parsing the upload log and try to upload everything not found on the server.
    drive_loc : os.path.abspath
        The specific location on the mounted drive to start searching for AHAP imagery.
    dryrun : BOOLEAN
        True to print actions without performing.
    verbose : BOOLEAN
        Set logger level to DEBUG, screw up progress bar.
    prj_dir : os.path.abspath
        Directory to write logs to.

    Returns
    -------
    None.

    """
    #### Logging setup
    upload_log = os.path.join('ahap_uploaded_files.txt')
    log = os.path.join(prj_dir, 'ahap_upload.log')
    if verbose:
        log_level = 'DEBUG'
    else:
        log_level = 'INFO'
    # create logger
    logger = create_logger('ahap_upload.py', 'sh', handler_level=log_level)
    logger = create_logger('ahap_upload.py', 'fh', handler_level=log_level, filename=log)
    
    
    # TODO: Necessary?
    # Create file to log files that were uploaded to server
    if not os.path.exists(upload_log):
        logger.debug('Creating file to list uploaded files at: {}'.format(upload_log))
        with open(upload_log, 'w') as ul:
            ul.write('')
    # Uploaded files
    with open(upload_log) as ul:
        logger.debug('Reading previously uploaded files to skip...')
        uploaded = ul.readlines()
    
    
    # If drives are explicitly provided, use only those
    if drives:
        active_drives = ['{}:'.format(d) for d in drives]
    else:
        # Get all active drives - all drives mounted (Not C:)
        active_drives = get_active_drives()
        active_drives = [d for d in active_drives if os.path.ismount(d)]
    logger.debug('Active drives: {}'.format('\n'.join(active_drives)))
    
    
    # Get aerial imagery drives
    # First level subdirectories on drives are './hsm{num}/' or './AHAP Tif files' or ./photos/hsm_
    aerial_imagery_subdirs = ['hsm{}'.format(x) for x in range(0,10)]
    aerial_imagery_subdirs.append('AHAP Tif files')
    aerial_imagery_subdirs.append('photos')
    aerial_imagery_subdirs.append('hsm')
    # Check if any of the subdir patterns exist on mounted drives
    # ahap_drives = [d for d in active_drives 
    #                  if True in [os.path.exists(os.path.join(d, sd)) 
    #                              for sd in aerial_imagery_subdirs]]
    # Check if any of the subdir patterns (aerial_imagery_subdirs) 
    # exist on mounted drives
    ahap_drives = [d for d in active_drives
                   if True in [os.path.join(d, s).startswith(tuple([os.path.join(d, sd) 
                                                   for sd in aerial_imagery_subdirs])) 
                               for s in os.listdir(d)]]
    
    logger.info('AHAP Drives: {}'.format(' '.join(ahap_drives)))
    
    
    # Get AHAP filepaths, filenames start with '57', '58' '63', '64'
    ahap_filename_prefixes = ('57', '58', '63', '64')
    drive_ahap_files = []
    for ad in ahap_drives:
        logger.info('Parsing files on drive: {}...'.format(ad))
        # If a specific location on the drive is specified, skip to that location to begin search
        # This will speed parsing large drives
        if drive_loc:
            ad = drive_loc
        for root, dirs, files in os.walk(ad):
            # # dirs[:] = [d for d in dirs if d.startswith(tuple(aerial_imagery_subdirs))]
            # for d in dirs:
            #     if not d.startswith(tuple(aerial_imagery_subdirs)):
            #         dirs.remove(d)
            
            ahap_files = [os.path.join(root, f) for f in files
                          if f.startswith(ahap_filename_prefixes)]
            drive_ahap_files.extend(ahap_files)
      
    logger.info('Total AHAP files found: {}'.format(len(drive_ahap_files)))
    
    if len(drive_ahap_files) == 0:
        logger.info('No AHAP files found, exiting...')
        sys.exit()
    
    
    # Create dataframe to join to danco table (danco table has destination paths)
    logger.debug('Joining located AHAP imagery IDs to danco table to obtain destination filepaths...')
    master_df = pd.DataFrame({'src':drive_ahap_files,
                              'filename':[os.path.split(x)[-1] for x in drive_ahap_files]})
    master_df['drive'] = master_df['src'].str[0]
    # Load danco table
    aia = query_footprint('usgs_index_aerial_image_archive', 
                          db='imagery', 
                          table=True, 
                          where="campaign = 'AHAP'")
    
    # Join to table to get resolution and filepath
    master_df = master_df.merge(aia, how='inner',
                                left_on='filename', right_on='filename')
    
    # Create resolution sub directory name ('med' or 'high') based on 'series' in table
    master_df['res_dir'] = master_df['series'].apply(lambda x: det_res_dir(x))
    
    # Convert unix style path to os style (i.e. windows)
    master_df['filepath'] = master_df['filepath'].str.replace(posixpath.sep, os.sep)
    
    # Create server path for each image (where it would be if it existed / where it should go)
    # TODO: make this nicer
    master_df['server_path'] = (server_loc + 
                                os.path.sep + 
                                master_df.apply(lambda x: det_server_path(x), axis=1))
    logger.debug('Server paths found: {}'.format(len(master_df[master_df['server_path']==''])))
    
    #### Check for existence on server
    ## TODO: speed this up - bottleneck - checking log first is an attempt to speed up the server check
    logger.info('Checking for existence of drive imagery on server...')
    if skip_log:
        master_df['online'] = False
    else:
        # Check if filenames are in log of what has been uploaded
        master_df['online'] = np.where(master_df['filename'].isin(uploaded), True, False)
    # Check the rest of the filenames against what is actually on server
    master_df['online'] = master_df[master_df['online']==False]['server_path'].apply(lambda x: os.path.exists(x))
    
    ## Select files that are not online by either test (upload log and existence on server)
    offline = master_df[master_df['online']==False]
    if len(offline) == 0:
        logger.info("No image files on drives found that aren't on the server, exiting...")
        sys.exit()
    logger.info('Image files on drives not on server: {}'.format(len(offline)))
    
    
    #### Copy missing paths to server
    # Open list of uploaded files
    logger.info('Beginning upload to {}'.format(server_loc))
    with open(upload_log, 'a') as ul:
        for letter_drive in offline['drive'].unique():
            # Count of total offline files for progress bar
            offline_count = len(offline[offline['drive']==letter_drive])
            
            usgs_drive = list(offline[offline['drive']==letter_drive]['src_drive'].unique())[0]
            logger.debug('Image files on drive {} not on server: {}'.format(letter_drive[:2], 
                                                                      offline_count))
            logger.info('Transfering from drive: {} ({})'.format(letter_drive[:2], usgs_drive))
            # Do the actual copying to the server
            for src, dst in tqdm(zip(offline[offline['drive']==letter_drive]['src'], 
                                     offline[offline['drive']==letter_drive]['server_path']),
                                 total=offline_count):
                # Make directory tree if necessary
                dst_dir = os.path.dirname(dst)
                if not os.path.exists(dst_dir):
                    logger.debug('Making directories: {}'.format(dst_dir))
                    if not dryrun:
                        os.makedirs(dst_dir)
                logger.debug('Copying {} \n to {}'.format(src, dst))
                if not dryrun:
                    try:
                        shutil.copyfile(src, dst)
                    except PermissionError:
                        logger.debug('Permission error on {}'.format(os.path.basename(dst)))
                    if os.path.exists(dst):
                        logger.debug('{} uploaded successfully'.format(dst))
                        ul.write(src)
                        ul.write('\n')
    
                # TODO os.stat to confirm transfer?
            logger.info('Completed transferring: {}'.format(letter_drive[:2]))


def ahap_upload_status(server_loc):
    """
    Determine the status of all AHAP imagery.

    Returns
    -------
    None.

    """
    # Load danco table
    logger.info('Loading danco table of all AHAP imagery...')
    aia = query_footprint('usgs_index_aerial_image_archive', 
                      db='imagery', 
                      table=True, 
                      where="campaign = 'AHAP'")
    logger.info('Checking for existence on server...')
    # Build full server path
    # Create resolution sub directory name ('med' or 'high') based on 'series' in table
    aia['res_dir'] = aia['series'].apply(lambda x: det_res_dir(x))
    
    # Convert unix style path to os style (i.e. windows)
    aia['filepath'] = aia['filepath'].str.replace(posixpath.sep, os.sep)
    
    # Create server path for each image (where it would be if it existed / where it should go)
    # TODO: make this nicer
    aia['server_path'] = (server_loc + 
                          os.path.sep + 
                          aia.apply(lambda x: det_server_path(x), axis=1))
    
    # Check for existence
    aia['online'] = False
    aia['online'] = aia[aia['online']==False]['server_path'].apply(lambda x: os.path.exists(x))
    
    return aia

    
# ahap_upload(server_loc=r'V:\pgc\data\aerial\usgs\ahap\photos',
#             prj_dir=r'C:\ahap_upload',
#             drives='G')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--drives', nargs='+', default=None,
                        help='Parse only these drive letters.')
    # TODO: Rename this argument to just be destination
    parser.add_argument('--server_loc', type=os.path.abspath, default=r'V:\pgc\data\aerial\usgs\ahap\photos',
                        help='Path to upload imagery to.')
    parser.add_argument('--project_directory', type=os.path.abspath,
                        default=r'C:\ahap_upload',
                        help='Change directory to write logs to.')
    parser.add_argument('--drive_loc', type=os.path.abspath,
                        help="""Specific location on drive to start searching, will be applied to 
                                all drives.""")
    parser.add_argument('--skip_log', action='store_true',
                        help="""Use this flag to only check if file exists on server, not using the
                                log of previously uploaded files.""")
    parser.add_argument('--write_master', type=os.path.abspath, default=None,
                        help='Specify a filename to write a csv of upload status per AHAP file.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performiing.')
    parser.add_argument('--verbose', action='store_true',
                        help='Set logger level to DEBUG')

    
    args = parser.parse_args()
    
    # TODO: Fix this so that you can both write master and perform upload (after?)
    if args.write_master is not None:
        master = ahap_upload_status(args.server_loc)
        logger.info('Writing master AHAP status csv to: {}'.format(args.write_master))
        master.to_csv(args.write_master)
    else:
        ahap_upload(drives=args.drives,
                    server_loc=args.server_loc,
                    prj_dir=args.project_directory,
                    drive_loc=args.drive_loc,
                    skip_log=args.skip_log,
                    dryrun=args.dryrun,
                    verbose=args.verbose)
