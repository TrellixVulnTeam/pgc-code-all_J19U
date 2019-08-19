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

from RasterWrapper import Raster


#### Environment settings
tqdm.pandas()


#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def create_raster_lut(sea_ice_dir, year_start=1978, year_stop=2020, update=False):
    '''
    Creates a lookup dictionary for each raster in the sea ice
    raster directory.
    '''
    pickle_path = r'C:\Users\disbr007\projects\coastline\pickles\sea_ice_concentraion_index.pkl'
    if update == False:
        raster_index = pd.read_pickle(pickle_path)
    else:
        logger.info('Creating look-up table of sea-ice rasters by date...')
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
        
        pd.to_pickle(raster_index, pickle_path)
    
    return raster_index


def locate_sea_ice_path(footprint, raster_lut, date_col='acq_time'):
    '''
    Takes footprints in and looks up their acq_time (date) in the raster_lut to locate
    the path to the appropriate raster.
    '''
    acq_time = footprint[date_col]
    year, month, day = acq_time[:10].split('-')
    try:    
        # Try to locate raster for actual day. If not try the next day, if not try the day before
        if day in raster_lut[year][month].keys():
            sea_ice_p = raster_lut[year][month][day]
        
        elif str(int(day) + 1) in raster_lut[year][month].keys():
            sea_ice_p = raster_lut[year][month][str(int(day) + 1)]
        
        else:
            sea_ice_p = raster_lut[year][month][str(int(day) - 1)]
    except KeyError as e:
        print(e)
        print(acq_time)
        print(year, month, day)
        sea_ice_p = None
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
    
    sea_ice_concen = sea_ice.SampleWindow((y,x), (3,3), agg='mean', grow_window=True, max_grow=81)
    
    ## Convert to percentage
    sea_ice_concen = sea_ice_concen / 10
    
    return sea_ice_concen
    


## Create look up table of all sea-ice concentration rasters by date raster_lut['year']['month']['day'] = filename
sea_ice_dir = r'C:\Users\disbr007\projects\coastline\noaa_sea_ice\resampled_nd'
raster_lut = create_raster_lut(sea_ice_dir, update=False)


## Read in candidate footprints from initial selection criteria and coastline intersect
logger.info('Loading candidate footprints...')
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
cand_p = 'nasa_global_coastline_candidates'
cand = gpd.read_file(gdb, driver='OpenFileGDB', layer=cand_p)
#date_col = 'acqdate' # DG
#date_col = 'acq_time' # MFP
date_col = 'ACQ_TIME' # NASA ?
out_path = r'C:\Users\disbr007\projects\coastline\nasa_global_coastline_candidates_seaice.shp'

## Reproject, saving original crs
logger.info('Reprojecting footprints to EPGS:3413 to match sea-ice rasters...')
src_crs = cand.crs
cand = cand.to_crs({'init':'epsg:3413'})

## Change to centroid, saving original geometry
logger.info('Getting footprint center point coordinates for sampling...')
cand['geom_poly'] = cand.geometry
cand['geom_cent'] = cand.centroid
cand.drop(columns='geometry', inplace=True)
cand.set_geometry('geom_cent', inplace=True)

# Get center point coordinates
cand['yx'] = cand.apply(get_center_yx, args=('geom_cent',), axis=1)

# Locate sea ice path for each footprint
logger.info('Looking up path to sea-ice raster for each footprint...')
cand['sea_ice_path'] = cand.apply(locate_sea_ice_path, args=(raster_lut, date_col), axis=1)

# Sample sea ice rasters - try sorting to speed up
logger.info('Sampling sea-ice rasters...')
cand.sort_values(by=[date_col], inplace=True)
cand['sea_ice_concen'] = cand.progress_apply(sample_sea_ice, args=('yx',), axis=1)


## Switch back to polygon geometry
logging.info('Writing to shapefile...')
cand.set_geometry('geom_poly', inplace=True)
cand['yx'] = cand['yx'].astype(str)

## Drop centroid geometry for writing to shape
cand.drop(columns='geom_cent', inplace=True)

## Reproject back to original crs
cand.to_crs(src_crs)
cand.to_file(out_path, driver='ESRI Shapefile')


#### PLOTTING
def y_fmt(y, pos):
    '''
    Formatter for y axis of plots. Returns the number with appropriate suffix
    y: value
    pos: *Not needed?
    '''
    decades = [1e9, 1e6, 1e3, 1e0, 1e-3, 1e-6, 1e-9 ]
    suffix  = ["G", "M", "k", "" , "m" , "u", "n"  ]
    if y == 0:
        return str(0)
    for i, d in enumerate(decades):
        if np.abs(y) >=d:
            val = y/float(d)
            signf = len(str(val).split(".")[1])
            if signf == 0:
                return '{val:d} {suffix}'.format(val=int(val), suffix=suffix[i])
            else:
                if signf == 1:
                    if str(val).split(".")[1] == "0":
                       return '{val:d}{suffix}'.format(val=int(round(val)), suffix=suffix[i]) 
                tx = "{"+"val:.{signf}f".format(signf = signf) +"} {suffix}"
                return tx.format(val=val, suffix=suffix[i])
    return y


def plot_agg_timeseries(src_df, agg_col, agg_type, date_col, freq, ax=None):
    """
    df: dataframe to make histogram from
    agg_col: column to agg
    agg_type = type of aggregation on col -> 'count', 'sum', etc.
    date_col: column with date information, unaggregated
    freq: frequency of aggregation ('Y', 'M', 'D')
    ax: preexisting ax to plot on, defaults to creating a new one
    """
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    from matplotlib.ticker import FuncFormatter
    import matplotlib.dates as mdates
    import copy
    ## Prep data
    # Convert date column to pandas datetime and set as index
    df = copy.deepcopy(src_df)
    df[date_col] = pd.to_datetime(df[date_col])
    df.set_index(date_col, inplace=True)
    
    # Aggregate 
    agg = {agg_col: agg_type}
    agg_df = df.groupby([pd.Grouper(freq=freq)]).agg(agg)
    
    
    ## Plotting
    mpl.style.use('ggplot')
    if ax == None:
        fig, ax = plt.subplots(nrows=1, ncols=1)
    
    agg_df.plot.area(y=agg_col, ax=ax)
    
#    ax.xaxis.set_major_locator(mdates.YearLocator((range(2010, 2019, 1))))
#    ax.xaxis.set_minor_locator(mdates.MonthLocator((1,4,7,10)))
#    
#    ax.xaxis.set_major_formatter(mdates.DateFormatter("\n%Y"))
#    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%b"))
#    plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
    plt.show()
    return fig, ax

#plot_agg_timeseries(cand, 'sea_ice_concen', 'mean', 'acq_time', 'M')




