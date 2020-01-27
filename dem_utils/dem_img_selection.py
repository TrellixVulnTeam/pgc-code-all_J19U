# -*- coding: utf-8 -*-
"""
Select DEMs and imagery and copy from server.
"""

import os
import platform
import shutil

import pandas as pd
import geopandas as gpd

from query_danco import query_footprint
from raster_clip import warp_rasters
from gdal_tools import remove_shp, get_raster_sr, get_shp_sr, ogr_reproject, check_sr
from id_parse_utils import write_ids
from valid_data import valid_percent_clip
from logging_utils import create_logger


# TODO: speed up by reprojecting once when warping/checking valid percentage (workaround impl.)
# TODO: change writing of dem FP with valid percents to actual location, not scratch
# TODO: Double check duplicate DEMS for each AOI


# INPUTS
AOI_PATH = r'E:\disbr007\umn\ms\shapefile\aois\banks_aois.shp' 
AOI_SELECT = [('Name', 'test', 'str'), ('ID', '7', 'int')] # subset selection for AOI
# AOI_SELECT = [('Name', 'test', 'str')]
# AOI_SELECT = None
AOI_UNIQUE = 'OBJ_ID' # field in aoi shapefile with unique identifiers
MONTHS = [5, 6, 7, 8, 9, 10]
MULTISPEC = True
VALID_THRESH = 50 # threshold of valid data % over AOI to copy
PRJ_DIR = r'E:\disbr007\umn\ms' # project directory
OUT_DEM_DIR = None
OUT_ID_LIST = None
SCRATCH_DIR = None
SUMMARY_OUT = None
SHAPEFILE_DIR = None


# Create out directories and paths
if not OUT_DEM_DIR:
    OUT_DEM_DIR = os.path.join(PRJ_DIR, 'dems') # directory to write clipped DEMs to
if not OUT_ID_LIST:
    OUT_ID_LIST = os.path.join(PRJ_DIR, 'dem_ids.txt') # directory to write list of catalogids to
if not SCRATCH_DIR:
    SCRATCH_DIR = os.path.join(PRJ_DIR, 'scratch') # for writing reprojected DEMs
if not SHAPEFILE_DIR:
    SHAPEFILE_DIR = os.path.join(PRJ_DIR, 'shapefile')
if not SUMMARY_OUT:
    SUMMARY_OUT = os.path.join(PRJ_DIR, 'summary_thresh{}.xlsx'.format(VALID_THRESH)) # for writing summary statistics


# PARAMETERS
WINDOWS_OS = 'Windows' # value returned by platform.system() for windows
LINUX_OS = 'Linux' # value return by platform.system() for linux
WINDOWS_LOC = 'win_path' # field name of windows path in footprint
LINUX_LOC = 'filepath' # linux path field
DEM_FNAME = 'dem_name' # field name with filenames (with ext)
FULLPATH = 'fullpath' # created field in footprint with path to files
VALID_PERC = 'valid_percent' # created field in footprint to store valid %
DEM_SUB = 'dems' # DEM subdirectory, if not provided
DEMS_FP = 'pgc_dem_setsm_strips' # Danco DEM footprint tablename
CATALOGID = 'catalogid1' # field name in danco DEM footprint for catalogids
CLIP_SUBDIR = 'clip' # name of subdirectory in 'dems' to place clipped dems
DATE_COL = 'acqdate1' # name of date field in dems footprint
MONTH_COL = 'month' # name of field to create in dems footprint if months are requested 


# Create logger
logger = create_logger(os.path.basename(__file__), 'sh', handler_level='DEBUG')


def check_where(where):
    """Checks if the input string exists already"""
    if where:
        where += ' AND '
    return where


# Determine operating system for locating DEMs
OS = platform.system()


# Get DEM footprint crs - this loads no records, but it
# will allow getting the crs of the footprints
dems = query_footprint(DEMS_FP, where="1=2")

# Load AOI
aoi = gpd.read_file(AOI_PATH)
# If AOI selection criteria, subset AOI
if AOI_SELECT:
    for field, value, t in AOI_SELECT:
        if t == 'float':
            value = float(value)
        elif t == 'int':
            value = int(value)
        aoi = aoi[aoi[field]==value]
# Check coordinate system match
if aoi.crs != dems.crs:
    aoi = aoi.to_crs(dems.crs)
# Get bounds of aoi to reduce query size, with padding
minx, miny, maxx, maxy = aoi.total_bounds
pad = 10


# Load DEMs
# Build SQL clause to select DEMs in the area of the AOI, helps with load times
dems_where = """cent_lon > {} AND cent_lon < {} AND 
                cent_lat > {} AND cent_lat < {}""".format(minx-pad, maxx+pad, miny-pad, maxy+pad)
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


# Select by location
dems = gpd.overlay(dems, aoi, how='intersection')
# Remove duplicates resulting from intersection (not sure why DUPs)
dems = dems.drop_duplicates(subset=(DEM_FNAME))


# Create full path to server location, used for checking validity
if OS == WINDOWS_OS:
    server_loc = WINDOWS_LOC
    
elif OS == LINUX_OS:
    server_loc = LINUX_LOC    
    

dems[FULLPATH] = dems.apply(lambda x: os.path.join(x[server_loc], x[DEM_FNAME]), axis=1)
# dems[FULLPATH] = dems['full_path'].apply(lambda x: x.replace('/', os.sep))
# Subset to only those DEMs that actually can be found
# TODO: ask where these missing ones may be...
dems = dems[dems[FULLPATH].apply(lambda x: os.path.exists(x))==True]


# Ensure spatial references match to avoid reprojecting in gdal_tools.ogr_reproject
# when it's called as part of determining valid data percent
# Get a sample DEM path
# check_dem = dems[FULLPATH][:1][0]
# sr_match = check_sr(AOI_PATH, check_dem)
# if sr_match == False:
#     temp_prj_aoi = os.path.join(SCRATCH_DIR, 'temp_prj_aoi.shp')
#     ogr_reproject(AOI_PATH, get_raster_sr(check_dem), output_shp=temp_prj_aoi)
#     aoi = gpd.read_file(temp_prj_aoi)

    
# Iterate over AOIs, selecting only those DEMs that intersect the AOI 
# and determine valid percent or each DEM
min_dates = []
max_dates = []
dem_counts = []

master_catalogids = []
for a in aoi[AOI_UNIQUE].unique():
    # Select just the current AOI from the master AOIs, then write out to use
    # in determining valid percents
    temp_aoi_path = os.path.join(SCRATCH_DIR, 'temp.shp')
    temp_aoi = aoi[aoi[AOI_UNIQUE]==a]
    temp_aoi.to_file(temp_aoi_path)
    
    # Spatial intersection with current aoi
    aoi_dems = gpd.overlay(dems, temp_aoi, how='intersection')
    logger.debug('AOI: {}'.format(a))
    logger.debug('Intersecting DEMs found: {}'.format(len(aoi_dems)))
    logger.info('Computing valid percentages for DEMs in AOI {}...'.format(a))
    # Clip rasters and if valid percent is greater than threshold, write out
    aoi_dems[VALID_PERC] = aoi_dems[FULLPATH].apply(lambda x: valid_percent_clip(aoi=temp_aoi_path,
                                                                                  raster=x))
    # Write out the footprints with valid data percentages
    aoi_dems.to_file(os.path.join(SHAPEFILE_DIR, '{}_dems_valid.shp'.format(a)))
    # If no DEMs match criteria, exit
    if len(aoi_dems) == 0:
        continue
    
    # Reduce DEMS footprints to those above threshold, if provided
    if VALID_THRESH:
        aoi_dems = aoi_dems[aoi_dems[VALID_PERC] > VALID_THRESH]
        logger.debug('DEMs with valid data above threshold {}%: {}'.format(VALID_THRESH, 
                                                                            len(aoi_dems)))
        aoi_dems_paths = list(aoi_dems[FULLPATH])
        aoi_dem_dir = os.path.join(OUT_DEM_DIR, str(a), CLIP_SUBDIR)
        if not os.path.exists(aoi_dem_dir):
            os.makedirs(aoi_dem_dir)
        # Clip the DEMs to the current AOI
        logger.debug('Clipping to AOI...')
        warp_rasters(temp_aoi_path, aoi_dems_paths, out_dir=aoi_dem_dir,)
                      # out_prj_shp=os.path.join(SCRATCH_DIR, 'temp.shp'))
        
    # Write shapefile of footprints to file
    aoi_dems.to_file(os.path.join(PRJ_DIR, 'aoi{}_dems.shp'.format(a)))
    
    # Add catalogids to master list
    master_catalogids.extend(list(aoi_dems[CATALOGID]))
    # Write catalogids for this AOI
    write_ids(list(aoi_dems[CATALOGID]), os.path.join(PRJ_DIR, '{}_catalogids.txt'.format(a)))
    
    # Create summary statistics for AOI
    min_dates.append(aoi_dems.acqdate1.min())
    max_dates.append(aoi_dems.acqdate1.max())
    dem_counts.append(len(aoi_dems))
    
    # Remove the temp aoi shapefile
    temp_aoi = None
    # remove_shp(temp_aoi_path)
   

aoi_master_summary = pd.DataFrame({AOI_UNIQUE: list(aoi[AOI_UNIQUE]), 
                                    'min_date': min_dates,
                                    'max_date': max_dates,
                                    'dem_count': dem_counts})

# Write summary dataframe out
aoi_master_summary.to_excel(SUMMARY_OUT)
# Write catalogids out
write_ids(master_catalogids, OUT_ID_LIST)


    
# Get DEMs
# Create directory names if they aren't provided
# if not PRJ_DIR:
#     PRJ_DIR = os.getcwd()
# if not OUT_DEM_DIR:
#     DEMS_DIR = os.path.join(PRJ_DIR, DEM_SUB)
# if not OUT_ID_LIST:
#     CATIDS_P = os.path.join(PRJ_DIR, 'dem_catalogids.txt')
    
# # Create outpath
# if not os.path.exists(OUT_DEM_DIR):
#     os.makedirs(OUT_DEM_DIR)
# # # Copy DEMs down
# for dem_path, dem_name in zip(list(dems[FULLPATH]), list(dems[DEM_FNAME])):
#     out_path = os.path.join(OUT_DEM_DIR, dem_name)
#     shutil.copy2(dem_path, out_path)
