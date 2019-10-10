# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 15:24:04 2019

@author: disbr007
"""

import os
import logging


import fiona
import geopandas as gpd
from shapely.geometry import Point


def get_bounding_box(shp, gdf=False):
    '''
    returns the bounds of shp, alternatively as a gdf
    shp: path to shapefile
    '''
    # Initiate starting corners
    minx = 180.0
    miny = 90.0
    maxx = -180
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

def grid_aoi(aoi_shp, step=None, x_space=None, y_space=None, write=False):
    '''
    Create a grid of points over an AOI shapefile. Only one of 'step' or 'x_space' and 'y_space'
    should be provided.
    aoi_shp: path to shapefile of AOI - must be only one feature -> can be MultiPolygon
    step: number of rows and columns desired in output grid
    x_space: horizontal spacing in units of aoi_shp projection
    y_space: vertical spacing in units of aoi_shp projection
    '''
    driver = 'ESRI Shapefile'
    boundary = gpd.read_file(aoi_shp, driver=driver)
    with fiona.open(aoi_shp, 'r') as ds_in:
        crs = ds_in.crs
        # Determine bounds
        minx, miny, maxx, maxy = get_bounding_box(aoi_shp)
        range_x = (maxx - minx)
        range_y = (maxy - miny)
        
    # Set number of rows and cols for grid
    if step:
        # Determine spacing of points in units of polygon projection (xrange / step)
        x_space = range_x / step
        y_space = range_y / step
    
    # Create points (loop over number cols, inner loop number rows), add to list of gdfs of points
    x = minx
    y = miny
    points = []
    logging.info('Creating grid points...')
    for x_step in tqdm.tqdm(np.arange(minx, maxx+x_space, x_space)):
        y = miny
        for y_step in np.arange(miny, maxy+y_space, y_space):
            print('{:.2f}, {:.2f}'.format(x, y))
            the_point = Point(x,y)
            if the_point.intersects(boundary.geometry[0]):
                points.append(the_point)
            y += y_space
        x += x_space
    
    # Put points into geodataframe with empty 'count' column for storing count of overlapping fps
    col_names = ['count', 'geometry']
    points_gdf = gpd.GeoDataFrame(columns=col_names)
    points_gdf.crs = crs
    points_gdf['geometry'] = points
    if write:
        out_dir = os.path.dirname(aoi_shp)
        out_name = '{}_grid.shp'.format(os.path.basename(aoi_shp).split('.')[0])
        out_path = os.path.join(out_dir, out_name)
        points_gdf.to_file(out_path, driver=driver)

    return points_gdf