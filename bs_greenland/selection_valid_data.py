# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 14:44:39 2020

@author: disbr007
"""
import os

import geopandas as gpd
import pandas as pd
from osgeo import ogr
import numpy as np
from tqdm import tqdm

from valid_data import valid_data, valid_data_aoi
from gdal_tools import check_sr
from clip2shp_bounds import warp_rasters
from logging_utils import create_logger


logger = create_logger('selection_valid_data.py', 'sh', 'DEBUG')


def create_subdir(BoxID):
    """
    Takes an INT and returns the hundreds it
    belongs to E.g. 3 becomes 000, 251 becomes
    200.
    """
    bid = str(BoxID).zfill(3)
    first = bid[0]
    subdir = '{}00'.format(first)
    return subdir


# Project directory
prj_dir = r'E:\disbr007\UserServicesRequests\Projects\kbollen'
# For writing individual shapefiles for each AOI
temp_dir = os.path.join(prj_dir, 'temp')
# Master CSV of clipped DEM locations and valid data %
MASTER_OUT = os.path.join(prj_dir, 'clipped_footprints.csv')
COUNTS_OUT = os.path.join(prj_dir, 'valid_data_counts.csv')

# Create output directories
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)
dem_dir = os.path.join(prj_dir, 'dems')
if not os.path.exists(dem_dir):
    os.makedirs(dem_dir)


# Inputs
selection_path = r'E:\disbr007\UserServicesRequests\Projects\kbollen\master_dem_selection.shp'
aoi_path = r'E:\disbr007\UserServicesRequests\Projects\kbollen\TerminusBoxes\GreenlandPeriph_BoxesUpdated_prj.shp'


# Load inputs   
# Path to selection footprint
selection = gpd.read_file(selection_path)
# Path to shapefile of polygon AOIs
aoi = gpd.read_file(aoi_path)

# Try to load master record of what has been clipped
if os.path.exists(MASTER_OUT):
    master = pd.read_csv(MASTER_OUT)
    record = True
else:
    # Create master dataframe of what is actually being written
    master = pd.DataFrame()
    record = False


ctr = 0 # counter for testing
record = False # for testing

# Iterate over each polygon in the AOI shapefile
for bid in tqdm(aoi.BoxID.unique()):
    # AOI for current BoxID
    aoi_bid = aoi[aoi.BoxID==bid]    
    # Copy current AOI polygon to a temp location 
    aoi_temp_p = os.path.join(temp_dir, 'aoi_temp{}.shp'.format(bid))
    if not os.path.exists(aoi_temp_p):
        aoi_bid.to_file(aoi_temp_p)
    ctr+=1
    if ctr >= 2:
        break
    
ctr = 0

for bid in aoi.BoxID.unique():
    print(ctr)
    aoi_temp_p = os.path.join(temp_dir, 'aoi_temp{}.shp'.format(bid))
    out_prj_shp = os.path.join(temp_dir, 'prj', 'aoi_temp{}_prj.shp'.format(bid))
    if not os.path.exists(os.path.dirname(out_prj_shp)):
        os.makedirs(os.path.dirname(out_prj_shp))
    
    # Selection of DEMs for the current BoxID
    s_bid = selection[selection.BoxID==bid]
    
    s_bid = s_bid[:10] # SUBSET for testing
    
    # Create path to dems on windows
    s_bid['dem_path'] = s_bid.apply(lambda x: os.path.join(x['win_path'], x['dem_name']), axis=1)
    s_bid['dem_valid'] = s_bid['dem_path'].apply(lambda x: os.path.exists(x))
    s_bid = s_bid[s_bid['dem_valid']==True]
    # rasters = list(s_bid[s_bid['dem_valid']==True]['dem_path'])
    rasters = list(s_bid['dem_path'])
    if record is True:
        rasters = [r for r in rasters if r not in master['dem_path']]
    
    # Create subdirectory for DEMs for each group of 100 box IDs
    subdir_hund_name = create_subdir(bid)
    subdir_hund = os.path.join(dem_dir, subdir_hund_name)
    if not os.path.exists(subdir_hund):
        os.makedirs(subdir_hund)
    subdir_bid = os.path.join(subdir_hund, str(bid))
    if not os.path.exists(subdir_bid):
        os.makedirs(subdir_bid)
    
    warp_rasters(aoi_temp_p, rasters, subdir_bid, out_suffix='_clip{}'.format(bid),
                 out_prj_shp=out_prj_shp)

    # Create outpath
    s_bid['out_path'] = s_bid['dem_name'].apply(lambda x: os.path.join(subdir_bid, 
                                                                       x.replace('.tif', '_clip{}.tif'.format(bid)))) 
    s_bid['dem_path'].str.replace('.tif', '_clip{}.tif'.format(bid))    
    s_bid['valid_data'] = s_bid.apply(lambda x: valid_data_aoi(aoi=aoi_temp_p, raster=x['out_path']), axis=1)
    
    master = pd.concat([master, s_bid], sort=True)
    
    os.remove(aoi_temp_p)
    
    ctr += 1
    if ctr >= 2:
        break
    
# Write master record of clipped DEMs
master.to_csv(os.path.join(prj_dir, MASTER_OUT))

# Statistics
counts = pd.DataFrame({'BoxID': [x for x in master['BoxID'].unique()]})
for val in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]:
    # val_words = round(val, 1)
    master['valid_{}'.format(val)] = master['valid_data'].apply(lambda x: x >= val)
    val_ct = master[master['valid_{}'.format(val)]==True].groupby(['BoxID']).agg({'dem_name':'count'})
    val_ct.rename(columns={'dem_name': 'valid_{}'.format(val)}, inplace=True)
    counts = counts.merge(val_ct, how='left', on='BoxID')

counts.to_csv(os.path.join(prj_dir, COUNTS_OUT))