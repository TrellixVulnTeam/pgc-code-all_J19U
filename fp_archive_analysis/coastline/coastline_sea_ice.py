# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 13:44:03 2019

@author: disbr007
Use Sea-Ice concentration rasters to further refine selection
"""

import geopandas as gpd
import pandas as pd
import os, logging

from RasterWrapper import Raster


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)
logger.setLevel(logging.INFO)


def create_raster_lut(sea_ice_dir, year_start=1978, year_stop=2020):
    '''
    Creates a lookup dictionary for each raster in the sea ice
    raster directory.
    '''
    ## Initialize empty dictionary with entries for each year, month, and day
    years = [str(year) for year in range(year_start, year_stop+1)]
    months = [str(month) if len(str(month))==2 else '0'+str(month) for month in range(1, 13)]
    days = [str(day) if len(str(day))==2 else '0'+str(day) for day in range(1,32)]
    raster_index = {year: {month: {day: None for day in days} for month in months} for year in years}
    ## Walk rasters extracting date information
#    ctr = 0 
    for root, dirs, files in os.walk(sea_ice_dir):
        for f in files:
            # Only add concentration rasters
            if f.endswith('_concentration_v3.0.tif'):
                date = f.split('_')[1] # f format: N_ N_19851126_concentration_v3.0.tif
                year = date[0:4]
                month = date[4:6]
                day = date[6:8]
#                print(year, month, day)
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


def locate_sea_ice_path(footprint, raster_lut):
    '''
    Takes footprints in and looks up their acq_time (date) in the raster_lut to locate
    the path to the appropriate raster.
    '''
    acq_time = footprint['acq_time']
    year, month, day = acq_time[:10].split('-')
    # Try to locate raster for actual day. If not try the next day, if not try the day before
    if day in raster_lut[year][month].keys():
        sea_ice_p = raster_lut[year][month][day]
    
    elif str(int(day) + 1) in raster_lut[year][month].keys():
        sea_ice_p = raster_lut[year][month][str(int(day) + 1)]
    
    else:
        sea_ice_p = raster_lut[year][month][str(int(day) - 1)]
    
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
    
    sea_ice = Raster(footprint['sea_ice_path'])
    
    sea_ice_concen = sea_ice.SampleWindow((y,x), (3,3), agg='mean')
    
    ## Convert to percentage
    sea_ice_concen = sea_ice_concen / 10
    
    return sea_ice_concen
    



## Create look up table of all sea-ice concentration rasters by date raster_lut['year']['month']['day'] = filename
logging.info('Creating look-up table of sea-ice rasters by date...')
sea_ice_dir = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\resampled_nd'

raster_lut = create_raster_lut(sea_ice_dir)

## Read in candidate footprints from initial selection criteria and coastline intersect
#logging.info('Reading in initial candidates...')
cand_p = r'C:\Users\disbr007\projects\coastline\scratch\initial_selection_greenland.pkl'

cand = pd.read_pickle(cand_p)

# Reproject
#logging.info('Reprojecting footprints to EPSG 3413...')

cand = cand.to_crs({'init':'epsg:3413'})

## Change to centroid, saving original geometry
#logging.info('Converting footprints to centroids...')

cand['geom_poly'] = cand.geometry
cand['geom_cent'] = cand.centroid
cand.drop(columns='geometry', inplace=True)
cand.set_geometry('geom_cent', inplace=True)

# Get center point coordinates
#logging.info('Getting center coordinates...')

cand['yx'] = cand.apply(get_center_yx, args=('geom_cent',), axis=1)

# Locate sea ice path for each footprint
#logging.info('Looking up sea-ice raster path for each candidate footprint...')

cand['sea_ice_path'] = cand.apply(locate_sea_ice_path, args=(raster_lut,), axis=1)

# Sample sea ice rasters - try sorting to speed up
logging.info('Sampling sea-ice rasters...')

cand['sea_ice_concen'] = cand.apply(sample_sea_ice, args=('yx',), axis=1)

## Switch back to polygon geometry
cand.set_geometry('geom_poly', inplace=True)
cand['yx'] = cand['yx'].astype(str)






