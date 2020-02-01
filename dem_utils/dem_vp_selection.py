# -*- coding: utf-8 -*-
"""
Created on Sat Feb  1 10:33:19 2020

@author: disbr007
"""

import matplotlib.pyplot as plt
import os

import pandas as pd
import geopandas as gpd



#### INPUTS ####
dems_p = r'E:\disbr007\umn\ms\shapefile\dem_footprints\banks_multispec_lewk_vp.shp'
# MONTHS = [5, 6, 7, 8, 9, 10]
MONTHS = [i for i in range(13)] # all months
MIN_DATE = ''
MAX_DATE = ''
MULTISPEC = True
VALID_THRESH = 50 # threshold of valid data % over AOI to copy
PRJ_DIR = r'E:\disbr007\umn\ms' # project directory
SELECTION_OUT = os.path.join(PRJ_DIR, 'shapefile', 'dem_footprints', 
                             '{}_selection.shp'.format(os.path.basename(dems_p).split('.')[0]))
OUT_DEM_DIR = None # Directory to write DEMs to 


#### PARAMETERS ####
WINDOWS_OS = 'Windows' # value returned by platform.system() for windows
LINUX_OS = 'Linux' # value return by platform.system() for linux
WINDOWS_LOC = 'win_path' # field name of windows path in footprint
LINUX_LOC = 'filepath' # linux path field
DEM_FNAME = 'dem_name' # field name with filenames (with ext)
FULLPATH = 'fullpath' # created field in footprint with path to files
VALID_PERC = 'valid_perc' # field in footprint storing valid %
# DEM_SUB = 'dems' # DEM subdirectory, if not provided
CATALOGID = 'catalogid1' # field name in danco DEM footprint for catalogids
CLIP_SUBDIR = 'clip' # name of subdirectory in 'dems' to place clipped dems
DATE_COL = 'acqdate1' # name of date field in dems footprint
SENSOR = 'sensor1' # name of sensor field in dems footprint
MONTH_COL = 'month' # name of field to create in dems footprint if months are requested 
MONTH_BOOL = 'req_month' # Name of column created to hold True/False if DEM in requested months
MULTISPEC_BOOL = 'multispec' # Name of column created to hold True/False if DEM is multispec


#### SUBSET INPUT FOOTPRINT ####s
dems = gpd.read_file(dems_p)

## Months selection
if MONTHS:
    dems['temp_date'] = pd.to_datetime(dems[DATE_COL])
    dems[MONTH_COL] = dems['temp_date'].dt.month
    dems.drop(columns=['temp_date'], inplace=True)
    # dems[MONTH_BOOL] = dems[MONTH_COL].isin(MONTHS)
    dems = dems[dems[MONTH_COL].isin(MONTHS)]

if MULTISPEC:
    # dems[MULTISPEC_BOOL] = dems['sensor1'].isin(['WVO2', 'WV03'])
    dems = dems[dems[SENSOR].isin(['WV01', 'WV02'])]
    
    
#### Write selection out ####
# dems.to_file(SELECTION_OUT)



plt.style.use('ggplot')
fig, ax = plt.subplots(1,1)
axes = dems.hist(column=MONTH_COL, ax=ax, edgecolor='w')
