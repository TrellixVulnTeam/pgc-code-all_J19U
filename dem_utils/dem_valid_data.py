# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 21:03:01 2020

@author: disbr007
"""

import os
import platform

import pandas as pd
import geopandas as gpd
from osgeo import gdal, ogr
from tqdm import tqdm
from datetime import datetime

from query_danco import query_footprint
from valid_data import valid_percent_clip
from logging_utils import create_logger
from gdal_tools import remove_shp


# Inputs
PRJ_DIR = r'E:\disbr007\umn\ms'
LOG_FILE = os.path.join(PRJ_DIR, 'logs', 'dem_valid_data.log')
# Path to DEMs to compute valid percentage on
DEMS_PATH = os.path.join(PRJ_DIR, r'shapefile\dem_footprints\banks_dems_multispec.shp')
# Path to write text file of dem_ids and percent valid
PROCESSED = os.path.join(PRJ_DIR, 'logs', 'dem_id_valid_percentage.txt')
# Path to write DEM footprints with valid percentage column
OUT_SHP = os.path.join(PRJ_DIR, r'ms\shapefile\dem_footprints\banks_dems_multispec_valid.shp')
SCRATCH_DIR = os.path.join(PRJ_DIR, 'scratch')
# DEM loading + selection criteria
DEMS_FP = 'pgc_dem_setsm_strips'
min_lat = None
max_lat = None
min_lon = None
max_lon = None
MULTISPEC = True
MONTHS = [5, 6, 7, 8, 9, 10]

gdal.UseExceptions()
ogr.UseExceptions()

# Parameters
WINDOWS_OS = 'Windows' # value returned by platform.system() for windows
LINUX_OS = 'Linux' # value return by platform.system() for linux
DATE_COL = 'acqdate1'
MONTH_COL = 'month'
DEM_FNAME = 'dem_name' # field name with filenames (with ext)
FULLPATH = 'fullpath' # created field in footprint with path to files
WINDOWS_LOC = 'win_path' # field name of windows path in footprint
LINUX_LOC = 'filepath' # linux path field


def check_where(where):
    """Checks if the input string exists already"""
    if where:
        where += ' AND '
    return where


def valid_dem_fp(dem_geometry, dem_path, dem_crs, scratch_dir):
    dem_fp = gpd.GeoDataFrame(geometry=[dem_geometry], crs=dem_crs)
    dem_fp_temp = os.path.join(scratch_dir, os.path.basename(dem_path).replace('.tif', '.shp'))
    dem_fp.to_file(dem_fp_temp)

    vp = valid_percent_clip(dem_fp_temp, dem_path)
    
    remove_shp(dem_fp_temp)
    
    return vp


# Create logger
if not __file__:
    __file__ = 'dem_valid_data.py'
logger = create_logger(__file__, 'sh')
logger = create_logger(__file__, 'fh', handler_level='DEBUG', filename=LOG_FILE)


logger.info('Loading DEMs...')
# If no footprint is provided, load all DEMs over input AOI coordinates
if DEMS_PATH is None:
    # Determine operating system for locating DEMs
    OS = platform.system()
        
    # Load DEMs
    # Build SQL clause to select DEMs in the area of the AOI, helps with load times
    pad = 5
    dems_where = """cent_lon > {} AND cent_lon < {} AND 
                    cent_lat > {} AND cent_lat < {}""".format(min_lon-pad, 
                                                              min_lon+pad, 
                                                              min_lat-pad, 
                                                              max_lat+pad)
    # Add to SQL clause to just select multispectral sensors
    if MULTISPEC:
        dems_where = check_where(dems_where)
        dems_where += """sensor1 IN ('WV02', 'WV03')"""
    
    # Actually load
    dems = query_footprint(DEMS_FP, where=dems_where)
    
    # If only certain months requested, reduce to those
    if MONTHS:
        dems['temp_date'] = pd.to_datetime(dems[DATE_COL])
        dems[MONTH_COL] = dems['temp_date'].dt.month
        dems.drop(columns=['temp_date'], inplace=True)
        dems = dems[dems[MONTH_COL].isin(MONTHS)]

else:
    dems = gpd.read_file(DEMS_PATH)
    

# Create full path to server location, used for checking validity
# Determine operating system for locating DEMs
OS = platform.system()
if OS == WINDOWS_OS:
    server_loc = WINDOWS_LOC
elif OS == LINUX_OS:
    server_loc = LINUX_LOC    

dems[FULLPATH] = dems.apply(lambda x: os.path.join(x[server_loc], x[DEM_FNAME]), axis=1)
# Subset to only those DEMs that actually can be found
dems = dems[dems[FULLPATH].apply(lambda x: os.path.exists(x))==True]
logger.info('DEMs found: {}'.format(len(dems)))


# Get valid percentage for all DEMs
logger.info('Determining valid percentage of DEMs...')
# If a file containing dem_id and valid percentages is passed, open and read them in.
if os.path.exists(PROCESSED):
    dem_ids_vps = []
    with open(PROCESSED, 'r') as p:
        content = p.readlines()
        for line in content:
            dem_id, vp = line.split(',')
            dem_ids_vps.append(dem_id, vp)
else:
    dem_ids_vps = []            


with open(PROCESSED, 'a') as p:
    for row in tqdm(dems[['dem_id', 'fullpath', 'geometry']].itertuples(index=False), 
                    total=len(dems)-len(dem_ids_vps)):
        dem_ids_processed = [x[0] for x in dem_ids_vps]
        if row.dem_id not in dem_ids_processed:
            try:
                vp = valid_dem_fp(row.geometry, row.fullpath, dems.crs, SCRATCH_DIR)
            except Exception as e:
                logger.error('Error with file: {}'.format(row.fullpath))
                logger.error(e)
                vp = -9999
        dem_ids_vps.append((row.dem_id, vp))
        p.write('{},{}'.format(row.dem_id, vp))

vps = pd.DataFrame({'dem_id': [x[0] for x in dem_ids_vps],
                    'valid_perc': [x[1] for x in dem_ids_vps]})

dems = dems.merge(vps, left_on='dem_id', right_on='dem_id')

logger.info('Writing DEM footprints with valid percentages to file...')
dems.to_file(OUT_SHP)
