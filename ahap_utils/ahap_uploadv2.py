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

import numpy as np
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
#from tqdm.auto import tqdm

from query_danco import query_footprint


parse_drives = None
server_loc = r'V:\pgc\data\aerial\usgs\ahap\photos'
log = 'ahap_upload.log'
dryrun = False
list_src_drives = False
verbose = True


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


# Create file to log files that were uploaded to server
upload_log = 'ahap_uploaded_files.txt'
if not os.path.exists(upload_log):
    with open(upload_log, 'w') as ul:
        ul.write('')
# Uploaded files
with open(upload_log) as ul:
    uploaded = ul.readlines()



# Get all active drives
active_drives = get_active_drives()
active_drives = [d for d in active_drives if os.path.ismount(d)]

## Get aerial imagery drives
# first level subdirectories on drives are ./hsm/ or ./AHAP Tif files
aerial_imagery_subdirs = ['hsm{}'.format(x) for x in range(0,10)]
aerial_imagery_subdirs.append('AHAP Tif files')
# Check if either of the subdir patterns exist on mounted drives
ahap_drives = [d for d in active_drives 
                 if True in [os.path.exists(os.path.join(d, sd)) 
                             for sd in aerial_imagery_subdirs]]

## Get AHAP filepaths, start with '57', '58' '63', '64'
ahap_filename_prefixes = ('57', '58', '63', '64')
drive_ahap_files = []
for ad in ahap_drives:
    logger.info('Parsing files on drive: {}...'.format(ad))
    for root, dirs, files in os.walk(ad):
        ahap_files = [os.path.join(root, f) for f in files 
                      if f.startswith(ahap_filename_prefixes)]
        drive_ahap_files.extend(ahap_files)

## Create dataframe to join to danco table
master_df = pd.DataFrame({'src':drive_ahap_files,
                          'filename':[os.path.split(x)[-1] for x in drive_ahap_files]})
master_df['drive'] = master_df['src'].str[0]

aia = query_footprint('usgs_index_aerial_image_archive', 
                      db='imagery', 
                      table=True, 
                      where="campaign = 'AHAP'")

## Join to table to get resolution and filepath
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


#### Check for existence on server
## TODO: speed this up - bottleneck
logger.info('Checking for existence of drive imagery on server...')
# Check if filenames are in log of what has been uploaded
master_df['online'] = np.where(master_df['filename'].isin(uploaded), True, False)
# Check the rest of the filenames against what is actually on server
master_df['online'] = master_df[master_df['online']==False]['server_path'].apply(lambda x: os.path.exists(x))

## Select files that are not online by either test (upload log and existence on server)
offline = master_df[master_df['online']==False]
logger.info('Image files on drives not on server: {}'.format(len(offline)))

#### Copy missing paths to server       
with open(upload_log, 'a') as ul:
    for letter_drive in offline['drive'].unique():
        # Count of total offline files for progress bar
        offline_count = len(offline[offline['drive']==letter_drive])
        
        usgs_drive = offline['src_drive'].unique()[0]
        logger.debug('Image files on drive {} not on server: {}'.format(letter_drive[:2], 
                                                                  offline_count))
        logger.info('Transfering from drive: {} ({})'.format(letter_drive[:2], usgs_drive))
        # Do the actual copying to the server
        for src, dst in tqdm(zip(offline[offline['drive']==letter_drive]['src'], 
                                 offline[offline['drive']==letter_drive]['server_path']),
                             total=offline_count):
            # Make directory tree if necessary
            dst_dir = os.path.dirname(dst)
#            if not os.path.exists(dst_dir):
#                logger.debug('Making directories: {}'.format(dst_dir))
#                if not dryrun:
#                    os.makedirs(dst_dir)
#            if not dryrun:
#                shutil.copyfile(src, dst)
#                ul.write(src)
#                ul.write('\n')
#                logger.debug('Copied {} \n to {}'.format(src, dst))
            # TODO os.stat to confirm transfer?
        logger.info('Completed transferring: {}'.format(letter_drive[:2]))




