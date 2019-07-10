# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:03:31 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import tqdm
from fiona.crs import from_epsg, from_string


def utm_area_calc(gdf):
    '''
    Takes a geodataframe in and calculates the area based on UTM zones of each feature. Returns
    a geodataframe with added 'utm_sqkm' column
    gdf: geodataframe
    '''
    ## Load UTM zones shapefile
    utm_zone_path = r'E:\disbr007\general\UTM_Zone_Boundaries\UTM_Zone_Boundaries.shp'
    utm_zones = gpd.read_file(utm_zone_path, driver='ESRI Shapefile')
    
    ## Locate zone of each feature based on centroid
    # Get original geometry column name
    geom_name = gdf.geometry.name
    # Get original list of columns - add new area col
    cols = list(gdf)
    area_col = 'sqkm_utm'
    cols.append(area_col)

    # Use centroid to locate UTM zone
    gdf['centroid'] = gdf.centroid
    gdf.set_geometry('centroid', inplace=True)
    gdf = gpd.sjoin(gdf, utm_zones, how='left', op='within')
    gdf.drop('centroid', axis=1, inplace=True)
    
    # Reset to original geometry
    gdf.set_geometry(geom_name, inplace=True)
    
    ## Loop through all zones found, reproject to relevant zone and calculate area
    gdf[area_col] = np.nan
    dfs_by_utm = []
    for utm_zone, df in tqdm.tqdm(gdf.groupby('Zone_Hemi')):
        zone = utm_zone.split(',')[0].replace(' ', '')
        hemi = utm_zone.split(',')[1].replace(' ', '')
        
        if hemi == 's':
            proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
        elif 'n':
            proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
        
        source_crs = gdf.crs
        df.geometry = df.geometry.to_crs(proj4)
        df.crs = from_string(proj4)
        df[area_col] = df.geometry.area / 10**6
        df.geometry = df.geometry.to_crs(source_crs)
        df.crs = source_crs
        dfs_by_utm.append(df)
    
    recombine = pd.concat(dfs_by_utm)
    recombine = recombine[cols]
    return recombine

# shp_path = r"E:\disbr007\general\geocell\geocells_quarter_.shp"

# driver = 'ESRI Shapefile'
# shp = gpd.read_file(shp_path, driver=driver)

# shp_areas = utm_area_calc(shp)
# shp_areas.to_file(r"E:\disbr007\general\geocell\geocells_quarter_sqkm.shp", driver=driver)


### SCRATCH - Plot areas
#import matplotlib.pyplot as plt

#fig, ax = plt.subplots(1,1)
##shp_areas['sqkm_utm'].plot.hist(bins=10)
#geocells = gpd.read_file(r'E:\disbr007\general\geocell\Global_GeoCell_Coverage.shp')
#geocells['AREA_SQKM'].astype(float).plot.hist(bins=30, edgecolor='white')






