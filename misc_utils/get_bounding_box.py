# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 15:34:38 2019

@author: disbr007
"""

import fiona
from shapely.geometry import Point, shape
import geopandas as gpd


def get_bounding_box(shp, gdf=False):
    '''
    returns the bounds of shp, alternatively as a gdf
    shp: path to shapefile
    '''
    # Initiate starting corners
    minx = 180.0
    miny = 90.0
    maxx = -180.0
    maxy = -90.0
    
    # Loop through features, if corner is outside current bounding box, update bounding box
    with fiona.open(shp, 'r') as ds_in:
        crs = ds_in.crs
        for feat in ds_in:
            geom = shape(feat['geometry'])
            # Determine bounds
            fminx, fminy, fmaxx, fmaxy = geom.bounds
            if fminx < minx:
                minx = fminx
            if fminy < miny:
                miny = fminy
            if fmaxx > maxx:
                maxx = fmaxx
            if fmaxy > maxy:
                maxy = fmaxy
    
        bounds = [minx, miny, maxx, maxy]
    
    # If geodataframe desired, create and return it
    if gdf:
        bbox = [Point(minx, miny), Point(minx, maxy), Point(maxx, miny), Point(maxx, maxy)]
        gdf = gpd.GeoDataFrame(crs=crs, columns=['geometry'])
        gdf['geometry'] = bbox
        return gdf
    
    else:
        return bounds