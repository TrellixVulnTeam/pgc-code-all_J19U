# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 13:44:03 2019

@author: disbr007
Use Sea-Ice concentration rasters to further refine selection
"""

import geopandas as gpd
import pandas as pd
import os
import copy


cand_p = r'C:\Users\disbr007\projects\coastline\scratch\initial_selection.pkl'
candidates = pd.read_pickle(cand_p)
sea_ice_dir = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\resampled_nd'


def create_raster_lut(year_start=1978, year_stop=2020):
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


def sample_dem(dem_array, pt, dem_gt=None, grid=(3,3)):
    '''
    Takes a dem that has been opened as an array and samples the value in a given
    grid size around the pt.
    dem_array: dem opened and read as array with GDAL
    dem_gt: dem geotransform
    pt: pt in geographic coordinates
    grid: tuple of (x-size, y-size)
    '''
    
    ## Convert point geocoordinates to array coordinates
    px = int((pt[0] - dem_gt[0]) / dem_gt[1])
    py = int((pt[1] - dem_gt[3]) / dem_gt[5])
    
    ## Get window around point
    x_sz = grid[0]
    x_step = int(x_sz / 2) # assuming int rounds down
    y_sz = grid[1]
    y_step = int(y_sz / 2)
    
    xmin = px - x_step
    xmax = px + x_step + 1 # slicing doesn't include stop val so add 1
    ymin = py - y_step
    ymax = py + y_step + 1
    
    window = dem_array[ymin:ymax, xmin:xmax]
    
    window_mean = window.mean()
    
    return window_mean



raster_lut = create_raster_lut()



