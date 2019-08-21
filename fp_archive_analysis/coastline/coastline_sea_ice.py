# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 13:44:03 2019

@author: disbr007
Use Sea-Ice concentration rasters to further refine selection
"""

import geopandas as gpd
import pandas as pd
import os, logging, sys
import numpy as np
from tqdm import tqdm
import copy

from RasterWrapper import Raster


#### Environment settings
#tqdm.pandas()
prj_path = r'C:\Users\disbr007\projects\coastline'

#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_raster_paths(sea_ice_dir, year_start=1978, year_stop=2020, update=False):
    '''
    Gets all of the raster paths for the given path and puts them in a dictionary
    sorted by year, month, day.
    sea_ice_dir: directory to parse
    '''
    ## Initialize empty dictionary with entries for each year, month, and day
    years = [str(year) for year in range(year_start, year_stop+1)]
    months = [str(month) if len(str(month))==2 else '0'+str(month) for month in range(1, 13)]
    days = [str(day) if len(str(day))==2 else '0'+str(day) for day in range(1,32)]
    raster_index = {year: {month: {day: None for day in days} for month in months} for year in years}
    
    for root, dirs, files in os.walk(sea_ice_dir):
        for f in files:
            # Only add concentration rasters
            if f.endswith('_concentration_v3.0.tif'):
                date = f.split('_')[1] # f format: N_ N_19851126_concentration_v3.0.tif
                year = date[0:4]
                month = date[4:6]
                day = date[6:8]
                raster_index[year][month][day] = os.path.join(root, f)

    ## Remove empty dictionary entries
    # Remove empty days
    for year_k, year_v in raster_index.copy().items():
        for month_k, month_v in raster_index[year_k].copy().items():
            for day_k, day_v in raster_index[year_k][month_k].copy().items():
                if day_v == None:
                    del raster_index[year_k][month_k][day_k]
    # Remove empty months
    for year_k, year_v in raster_index.copy().items():
        for month_k, month_v in raster_index[year_k].copy().items():
            if not month_v:
                del raster_index[year_k][month_k]
    # Remove empty years
    for year_k, year_v in raster_index.copy().items():
        if not year_v:
            del raster_index[year_k]
            
    return raster_index


def create_raster_lut(pole, year_start=1978, year_stop=2020, update=False):
    '''
    Creates a lookup dictionary for each raster in the sea ice
    raster directory.
    pole: 'arctic' or 'antarctic' to determine which rasters to sample
    '''
    ## Create a 'arctic_sea_ice_path' and 'antarctic_sea_ice_path - use lat to determine which to sample
#    pickle_path = r'C:\Users\disbr007\projects\coastline\pickles\sea_ice_concentraion_index.pkl'
    arctic_pickle_path = os.path.join(prj_path, r'pickles\arc_sea_ice_concentraion_index.pkl')
    antarctic_pickle_path = os.path.join(prj_path, r'pickles\ant_sea_ice_concentraion_index.pkl')
    if update == False:
#        raster_index = pd.read_pickle(pickle_path)
        if pole == 'arctic':
            raster_index = pd.read_pickle(arctic_pickle_path)
        elif pole == 'antarctic':
            raster_index = pd.read_pickle(antarctic_pickle_path)
    else:
        ## Concentration raster locations
        arctic_ice_dir = os.path.join(prj_path, r'noaa_sea_ice\north\resampled_nd\daily\geotiff')
        antarctic_ice_dir = os.path.join(prj_path, r'noaa_sea_ice\south\resampled_nd\daily\geotiff')
        
#        logger.info('Creating look-up table of sea-ice rasters by date...')
        ## Walk rasters extracting date information
        if pole == 'arctic':
            raster_index = get_raster_paths(arctic_ice_dir)
            pd.to_pickle(raster_index, arctic_pickle_path)
        elif pole == 'antarctic':
            raster_index = get_raster_paths(antarctic_ice_dir)
            pd.to_pickle(raster_index, antarctic_pickle_path)
        else:
            logging.ERROR('Unrecognized pole argument while creating raster lookup table: {}'.format(pole))
        
    return raster_index


def locate_sea_ice_path(footprint, yx_col, arctic_lut, ant_lut, date_col):
    '''
    Takes footprints in and looks up their acq_time (date) in the raster_lut to locate
    the path to the appropriate raster.
    footprint: footprint with date_col field
    pole: 'arctic' or 'antarctic'
    date_col: field with date in footprint
    '''
    ## Create a 'arctic_sea_ice_path' and 'antarctic_sea_ice_path - use lat to determine which to sample
    y = footprint[yx_col][0]
#    x = footprint[yx_col][1]

    acq_time = footprint[date_col]
    year, month, day = acq_time[:10].split('-')

    # Arctic
    if y >= 50.0:
        raster_lut = arctic_lut
        try:    
        
            # Try to locate raster for actual day. If not try the next day, if not try the day before
            if day in raster_lut[year][month].keys():
                sea_ice_p = raster_lut[year][month][day]
            
            elif str(int(day) + 1) in raster_lut[year][month].keys():
                sea_ice_p = raster_lut[year][month][str(int(day) + 1)]
            
            else:
                sea_ice_p = raster_lut[year][month][str(int(day) - 1)]
                
        except KeyError as e:
            print(e, 'KeyError')
            print(y)
            print(acq_time)
            sea_ice_p = None
            sys.exit()
    # Antarctic
    elif y <= -50.0:
        raster_lut = ant_lut
        try:    
        
            # Try to locate raster for actual day. If not try the next day, if not try the day before
            if day in raster_lut[year][month].keys():
                sea_ice_p = raster_lut[year][month][day]
            
            elif str(int(day) + 1) in raster_lut[year][month].keys():
                sea_ice_p = raster_lut[year][month][str(int(day) + 1)]
            
            else:
                sea_ice_p = raster_lut[year][month][str(int(day) - 1)]
                
        except KeyError as e:
            print(e, 'KeyError')
            print(y)
            print(acq_time)
            sea_ice_p = None
            sys.exit()
    # Nonpolar - no ice concentration data
    else:
        raster_lut = None ## Fix
        sea_ice_p = 'None'             
    
    return sea_ice_p


def get_center_yx(footprint, geom_col):
    '''
    Returns a tuple of the center y,x coordinates
    '''
    cent_yx = (footprint[geom_col].y, footprint[geom_col].x)
    return cent_yx


def sample_sea_ice(footprint, yx_col):
    '''
    Takes a footprint and determines the path to the appropriate raster, then samples
    the raster at that point
    '''
    y = footprint[yx_col][0]
    x = footprint[yx_col][1]

    ## Create a 'arctic_sea_ice_path' and 'antarctic_sea_ice_path - use lat to determine which to sample
    if footprint['sea_ice_path'] != 'None': ## FIX
        sea_ice = Raster(footprint['sea_ice_path'])
        sea_ice_concen = sea_ice.SampleWindow((y,x), (3,3), agg='mean', grow_window=True, max_grow=81)
        ## Convert to percentage
        sea_ice_concen = sea_ice_concen / 10
    else:
        sea_ice_concen = -9999
    return sea_ice_concen
    


## Create look up table of all sea-ice concentration rasters by date raster_lut['year']['month']['day'] = filename
sea_ice_dir = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\resampled_nd'
#raster_lut = create_raster_lut(sea_ice_dir, update=False)


## Read in candidate footprints from initial selection criteria and coastline intersect
logger.info('Loading candidate footprints...')

gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
src = 'nasa'

cand_p = '{}_global_coastline_candidates'.format(src)
cand = gpd.read_file(gdb, driver='OpenFileGDB', layer=cand_p)
date_col_lut = {
        'dg': 'acqdate',
        'mfp': 'acq_time',
        'nasa': 'ACQ_TIME',
        'oh': 'acq_time'}

date_col = date_col_lut[src]

#### *****FIX TO WRITE TO GDB - RECORDS GETTING CUTOFF****
out_path = r'C:\Users\disbr007\projects\coastline\{}_global_coastline_candidates_seaice.shp'.format(src)


## Reproject, saving original crs and center yx 
## Change to centroid, saving original geometry
logger.info('Getting footprint center point coordinates for sampling...')
cand['geom_poly'] = cand.geometry
cand['geom_cent'] = cand.centroid
cand.drop(columns='geometry', inplace=True)
cand.set_geometry('geom_cent', inplace=True)
# Get center point coordinates (assuming decimal degrees...)
cand['yx'] = cand.apply(get_center_yx, args=('geom_cent',), axis=1)

logger.info('Reprojecting footprints to EPGS:3413 to match sea-ice rasters...')
src_crs = cand.crs
cand = cand.to_crs({'init':'epsg:3413'})



#### Locate sea ice path for each footprint
logger.info('Looking up path to sea-ice raster for each footprint...')
#cand['sea_ice_path'] = cand.apply(locate_sea_ice_path, args=(raster_lut, date_col), axis=1)

## Create look up tables for arctic and antarctic
arctic_ice_lut = create_raster_lut('arctic', update=True)
ant_ice_lut = create_raster_lut('antarctic', update=True)

## Column names
sea_ice_path_col = 'sea_ice_path'

cand[sea_ice_path_col] = cand.apply(locate_sea_ice_path, args=('yx', arctic_ice_lut, ant_ice_lut, date_col), axis=1)

## Sample sea ice rasters - try sorting to speed up
logger.info('Sampling sea-ice rasters...')
cand.sort_values(by=[date_col], inplace=True)
#cand['sea_ice_concen'] = cand.progress_apply(sample_sea_ice, args=('yx',), axis=1) ## tqdm not working with pandas0.25
cand['sea_ice_concen'] = cand.apply(sample_sea_ice, args=('yx',), axis=1)


## Switch back to polygon geometry
logging.info('Writing to shapefile...')
cand.set_geometry('geom_poly', inplace=True)
cand['yx'] = cand['yx'].astype(str)

## Drop centroid geometry for writing to shape
cand.drop(columns='geom_cent', inplace=True)

## Reproject back to original crs
cand.to_crs(src_crs)

##### *****FIX TO WRITE TO GDB - RECORDS GETTING CUTOFF****
#cand.to_file(out_path, driver='ESRI Shapefile')
cand.to_file(r'C:\Users\disbr007\projects\coastline\coastline.gpkg',
             layer='{}_coastline_candidates_seaice'.format(src),
             driver='GPKG')

