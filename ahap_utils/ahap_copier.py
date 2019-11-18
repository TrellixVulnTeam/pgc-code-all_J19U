# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 13:49:34 2019

@author: disbr007
"""

import os
import logging
import shutil

import geopandas as gpd
from tqdm import tqdm

from query_danco import query_footprint


#### Logging setup
# create logger
logger = logging.getLogger('ahap_copier')
logger.setLevel(logging.DEBUG)
# create file handler
log = 'ahap_copier.log'
fh = logging.FileHandler(log)
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
logger.debug('Log file created at: {}'.format(log))


## Inputs
selection_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\3948\ahap\selected_ahap_photo_extents.shp'
dst_dir = r'C:\temp\ahap'
src_loc = 'drives'
DRYRUN = True

## Params
SERVER_LOC = os.path.normpath(r'V:\pgc\data\aerial\usgs\ahap\photos')
PHOTO_EXTENTS = 'Photo_Extents'
FLIGHTLINES = 'Flightlines'
CAMPAIGN = 'AHAP'
JOIN_SEL = 'PHOTO_ID'
JOIN_FP = 'UNIQUE_ID'
FP = 'usgs_index_aerial_image_archive'
DB = 'imagery'
FILEPATH = 'filepath'
FILENAME = 'filename'
SRC_DRIVE = 'src_drive'

DRIVE_PATH = 'drive_path'
RELATIVE_PATH = 'relative_path'
SERVER_PATH = 'server_path'
FROM_DRIVE = 'drives'
FROM_SERVER = 'server'
DST_PATH = 'dst'
SRC_PATH = 'src'

## Load selection
selection = gpd.read_file(selection_p)
selection_unique_ids = list(selection[JOIN_SEL].unique())
selection_unique_ids_str = str(selection_unique_ids).replace('[', '').replace(']', '')
## Determine type of selection input
selection_fields = list(selection)
if "PHOTO_ID" in selection_fields:
    selection_type = PHOTO_EXTENTS
else:
    selection_type = FLIGHTLINES
    

## Load aerial source table
# Build where clause, including selecting only ids in selection
where = "(sde.{}.{} IN ({}))".format(FP, JOIN_FP, selection_unique_ids_str)
aia = query_footprint(FP, db=DB, table=True, where=where)
# Convert path to os style -- only necessary for windows
aia[DRIVE_PATH] = aia[FILEPATH].apply(os.path.normpath)


## Get drive paths
drive_paths = aia[DRIVE_PATH].unique()


## Build server paths
def create_relative_paths(row):
    """
    Create relative path for each row
    """
    global FILENAME
    # Determine series subdir (high or low)
    if row['series'] == 'high_res':
        resolution = 'high'
    elif row['series'] == 'medium_res':
        resolution = 'low'

    relative_path = os.path.join(resolution, row[FILENAME])
    
    return relative_path


def find_drive_location(row, active_drives):
    """
    Check if each row (file) is on any of the active drives.
    If so return that drive letter.
    """
    # TODO: Figure out how to handle missing files -> subset aia before copying
    global DRIVE_PATH
    for letter in active_drives:
        filepath = os.path.join(letter, row[DRIVE_PATH])
        if os.path.exists(filepath):
            return filepath
        else:
            return 'NOT_MOUNTED'
            
            
    

aia[RELATIVE_PATH] = aia.apply(lambda x: create_relative_paths(x), axis=1)
aia[SERVER_PATH] = aia.apply(lambda x: os.path.join(SERVER_LOC, x[RELATIVE_PATH]), axis=1)


## Get src drives 
src_drives = list(aia[SRC_DRIVE].unique())
logger.info('Drives required for selection: {}'.format(src_drives))


## Retrieve
# Get all active drives
def get_active_drives():
    """
    List all active drives.
    """
    drive_list = []
    for drive in range(ord('A'), ord('Z')):
        if os.path.exists(chr(drive) + ':'):
            drive_list.append(chr(drive) + ':')
    return drive_list


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


aia[DST_PATH] = aia.apply(lambda x: os.path.join(dst_dir, x[RELATIVE_PATH]), axis=1)
if src_loc == FROM_DRIVE:
    aia[SRC_PATH] = aia[DRIVE_PATH]
elif src_loc == FROM_SERVER:
    aia[SRC_PATH] = aia[SERVER_PATH]

for src, dst in tqdm(zip(aia[DRIVE_PATH], aia[DST_PATH])):
    # Make directory tree if necessary
    dst_dir = os.path.dirname(dst)
    if not os.path.exists(dst_dir):
        logger.debug('Making directories: {}'.format(dst_dir))
        if not DRYRUN:
            os.makedirs(dst_dir)
        else:
            logger.info('Making directores: {}'.format(dst_dir))
        if not DRYRUN:
            shutil.copyfile(src, dst)
            logger.debug('Copied {} \n to {}'.format(src, dst))
        else:
            logger.info('Copying {} -> {}'.format(src, dst))
   
        # TODO os.stat to confirm transfer?
#    logger.info('Completed transferring: {}'.format(letter_drive[:2]))









