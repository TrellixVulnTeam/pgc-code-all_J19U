# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:03:31 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import tqdm
import copy
from fiona.crs import from_epsg, from_string


def area_calc(geodataframe, area_col='area_sqkm'):
    '''
    Takes a geodataframe in and calculates the area based 
    on UTM zones of each feature. Returns a geodataframe 
    with added 'utm_sqkm' column and 'polar_area' column 
    for those features north of south of utm zones boundaries
    geodataframe: geodataframe
    area_col: name of column to hold area
    '''
    gdf = copy.deepcopy(geodataframe)
    ## Load UTM zones shapefile
    utm_zone_path = r'E:\disbr007\general\UTM_Zone_Boundaries\UTM_Zone_Boundaries.shp'
    utm_zones = gpd.read_file(utm_zone_path, driver='ESRI Shapefile')
    
    ## Locate zone of each feature based on centroid
    # Get original geometry column name and original crs
    geom_name = gdf.geometry.name
    source_crs = gdf.crs
    # Get original list of columns - add new area col
    cols = list(gdf)
#    utm_area_col = 'sqkm_utm'
    utm_area_col = area_col
    pol_area_col = 'polar_area'
    cols.append(utm_area_col)
    cols.append(pol_area_col)
    gdf[utm_area_col] = np.nan
    gdf[pol_area_col] = np.nan

    # Use centroid to locate UTM zone
    gdf['centroid'] = gdf.centroid
    gdf.set_geometry('centroid', inplace=True)
    # Find points north and south of UTM zone boundary
    north_pole = gdf[gdf.centroid.y >= 84]
    south_pole = gdf[gdf.centroid.y <= -80]
    
    # Find all points that fall in a utm zone
    gdf = gpd.sjoin(gdf, utm_zones, how='left', op='within')
    gdf.drop('centroid', axis=1, inplace=True)
    
    # Reset to original geometry
    gdf.set_geometry(geom_name, inplace=True)
    
    ## Loop through all zones found, reproject to relevant utm zone and calculate area
    dfs_with_area = []
#    for utm_zone, df in tqdm.tqdm(gdf.groupby('Zone_Hemi')):
    for utm_zone, df in gdf.groupby('Zone_Hemi'):
        zone = utm_zone.split(',')[0].replace(' ', '')
        hemi = utm_zone.split(',')[1].replace(' ', '')
        
        if hemi == 's':
            proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
        elif hemi == 'n':
            proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
        
        df.geometry = df.geometry.to_crs(proj4)
        df.crs = from_string(proj4)
        df[utm_area_col] = df.geometry.area / 10**6
        df.geometry = df.geometry.to_crs(source_crs)
        df.crs = source_crs
        dfs_with_area.append(df)
    
    ## Calculate south pole areas using Anatarctic polar stereographic and north pole using Arctic polar stereographic
    for each_df, epsg in [(south_pole, '3031'), (north_pole, '3995')]:
        # Return to orginal geometry
        each_df.set_geometry(geom_name, inplace=True)
        each_df = each_df.to_crs({'init':'epsg:{}'.format(epsg)})
        each_df[pol_area_col] = each_df.geometry.area / 10**6
        each_df = each_df.to_crs(source_crs)
        dfs_with_area.append(each_df)
    recombine = pd.concat(dfs_with_area)
    recombine = recombine[cols]
    recombine[area_col] = np.where(recombine[area_col].isna(), recombine.polar_area, recombine[area_col])
    
    return recombine

