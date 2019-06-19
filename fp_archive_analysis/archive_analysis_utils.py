# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:05:51 2019

@author: disbr007
"""
import tqdm, subprocess, os, logging

import fiona
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import numpy as np
import multiprocessing
from joblib import Parallel, delayed

from query_danco import query_footprint
from get_bounding_box import get_bounding_box


## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(filename=r'E:\disbr007\scratch\fp_density.log', 
                    filemode='w', 
                    format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.DEBUG)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


def get_count(feat, init_sel):
    '''
    Perform spatial join of feat to init_sel and add column to feat with count of intersecting
    polygons in init_sel
    feat: one feature to count overlaps with
    fp_sel: gdf of polygons (footprints) to count
    '''
    sel4feat = gpd.sjoin(init_sel, feat, how='inner', op='intersects')
    feat['count'] = len(sel4feat)
    return feat


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    

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
    for x_step in tqdm.tqdm(np.arange(minx, maxx+x_space, x_space)):
        y = miny
        for y_step in np.arange(miny, maxy+y_space, y_space):
            the_point = Point(x,y)
            if the_point.within(boundary.geometry[0]):
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


def get_density(footprint, points_gdf, write_path=False):
    '''
    Gets the overlap count over each point in points geodataframe.
    footprint: danco footprint layer name
    points: geodataframe of points
    '''
    ## Count number of polygons over each point
    # Read in footprint to use
    fp = query_footprint(layer=footprint, columns=['catalogid', 'acqdate', 'cloudcover'])
    
    ## Do initial join to get all intersecting
    logging.info('Performing initial spatial join on entire AOI...')
    # Check projections are the same, if not reproject
    if fp.crs != points_gdf.crs:
        fp = fp.to_crs(points_gdf.crs)
    fp_sel = gpd.sjoin(fp, points_gdf, how='inner', op='intersects')
    fp_sel.drop(columns=['index_right'], inplace=True)
    del fp
    
    ## For each point in grid count overlaps
    # Split grid into individual gdfs
    logging.info('Splitting AOI into individual features...')
    split = [points_gdf.loc[[i]] for i in tqdm.tqdm(range(len(points_gdf)))]
    num_cores = multiprocessing.cpu_count() - 2
    # Run spatial joins in parallel to get counts
    logging.info('Performing spatial join on each feature in AOI...')
    results = Parallel(n_jobs=num_cores)(delayed(get_count)(i, fp_sel) for i in tqdm.tqdm(split))
    # Combine individual gdfs back into one
    density_results = pd.concat(results)
    
    ## Write grid out
    if write_path:
        out_path = os.path.join(write_path, 'density.shp')
        driver = 'ESRI Shapefile'
        try:
            density_results.to_file(out_path, driver=driver)
        except Exception as e:
            print(e)
    return density_results
    

def rasterize_grid(grid_path, count_field):
    '''
    Takes a point shapefile and rasterizes based on 'count' field
    '''
    ## Rasterize
    dir_name = os.path.dirname(grid_path)
    out_name = os.path.basename(grid_path).split(',')[0]
    out_path = os.path.join(dir_name, '{}_rasterize.tif'.format(out_name))
    
    gdal_bin = r"C:\OSGeo4W64\bin"
    gdal_grid = os.path.join(gdal_bin, 'gdal_grid.exe')
    command = '''{} -zfield "count" -a nearest -outsize 1000 1000 -ot UInt16 -of GTiff -l {} {} {}'''.format(gdal_grid, out_name, grid_path, out_path)
    
    run_subprocess(command)
    