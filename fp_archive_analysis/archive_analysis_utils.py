# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:05:51 2019

@author: disbr007
"""
import subprocess, os, logging
from tqdm import tqdm
import fiona
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import numpy as np
import multiprocessing
from joblib import Parallel, delayed
from copy import deepcopy
from query_danco import query_footprint
from get_bounding_box import get_bounding_box
from range_creation import range_tuples


## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)



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


def get_count(geocells, fps):
    '''
    Gets the count of features in fps that intersect with each feature in geocells
    geocells: geodataframe of polygons
    fps: geodataframe of polygons
    '''
    ## Confirm crs is the same
    if geocells.crs != fps.crs:
        logging.info('Converting crs of grid to match footprint...')
        geocells = geocells.to_crs(fps.crs)
    logging.info('Performing spatial join...')
    sj = gpd.sjoin(geocells, fps, how='left', op='intersects')
    sj.index.names = ['count']
    sj.reset_index(inplace=True)
    logging.info('Getting count...')
    gb = sj.groupby('count').agg({'count':'count'})
    out = gb.join(geocells)
    out = gpd.GeoDataFrame(out, geometry='geometry', crs=geocells.crs)
    return out


def get_count_loop(fxn, gcs, fps, 
                   lat_start=None, lat_stop=None, lat_step=None, 
                   lon_start=None, lon_stop=None, lon_step=None):
    '''
    **NEEDS more abstraction**
    Splits an AOI geodataframe (gcs) into a number of subsets and then loops over it,
    calling fxn with optional *args
    fxn: function to call in loop, must return dataframe or geodataframe
    gcs: geodataframe to split
    *args: any additional parameters to pass to fxn (gcs must be first)
    '''
    crs = gcs.crs
    
    ## Limit to given latititude and longitude
    # If both latitude and longitude params are set split by lon, then by lat, then combine into one list
    if lon_start and lat_start:
        lon_ranges = range_tuples(lon_start, lon_stop, lon_step)
        lat_ranges = range_tuples(lat_start, lat_stop, lat_step)
        split = [gcs[(gcs.Cent_Lon > x[0]) & (gcs.Cent_Lon <= x[1])] for x in lon_ranges]
        subsplit = [[df[(df.Cent_Lat > y[0]) & (df.Cent_Lat <= y[1])] for y in lat_ranges] for df in split]        
        split = [df for nestedlist in subsplit for df in nestedlist]
    # If latitude parameters are set - split based on those
    elif lat_start:
        lat_ranges = range_tuples(lat_start, lat_stop, lat_step)
        split = [gcs[(gcs.Cent_Lat > y[0]) & (gcs.Cent_Lat <= y[1])] for y in lat_ranges]
    # If longitude parameters are set - split based on those
    elif lon_start:
        lon_ranges = range_tuples(lon_start, lon_stop, lon_step)
        split = [gcs[(gcs.Cent_Lon > x[0]) & (gcs.Cent_Lon <= x[1])] for x in lon_ranges]
    # Simply split into four dfs of geocells
    else:
        split = [x for x in len(gcs)/4]
        
    print(split)
#    lon_ranges = [(-180, -90), (-90, 0), (0, 90), (90, 180)]
#    lat_ranges = [(-90, -45), (-45, 0), (0, 45), (45, 90)]
    
    results = []
#    for lst in tqdm(subsplit):
    for i, df in enumerate(split):
#        out_name = 'geocells_qtr_ct_{}.shp'.format(i+1)
#        out_path = os.path.join(r'E:\disbr007\scratch', out_name)
        out = fxn(df, fps)
        out = gpd.GeoDataFrame(out, geometry='geometry', crs=crs)
#        out.to_file(out_path, driver="ESRI Shapefile")
        results.append(out)
    
    return results



#def get_density(footprint, points_gdf, write_path=False):
#    '''
#    Gets the overlap count over each point in points geodataframe.
#    footprint: danco footprint layer name
#    points: geodataframe of points
#    '''
#    ## Count number of polygons over each point
#    # Read in footprint to use
#    fp = query_footprint(layer=footprint, columns=['catalogid', 'x1', 'y1'])
#
#    ## Do initial join to get all intersecting
#    logging.info('Performing initial spatial join with entire AOI...')
#    # Check projections are the same, if not reproject
#    if fp.crs != points_gdf.crs:
#        fp = fp.to_crs(points_gdf.crs)
#    # Perform spatial join
#    fp_sel = gpd.sjoin(fp, points_gdf, how='inner', op='intersects')
##    fp_sel = gpd.overlay(fp, points_gdf, how='intersection')
#    # Not sure why there are duplicate footprints but there are... 
#    fp_sel.drop_duplicates(subset=['catalogid'], keep='first', inplace=True)
#    fp_sel.drop(columns=['index_right'], inplace=True)
#
#    del fp
#    
#    ## For each point in grid count overlaps
#    # Split grid into individual gdfs
#    logging.info('Splitting AOI into individual features for parallel processing...')
#    try:
##        split = [points_gdf.iloc[[i]] for i in tqdm.tqdm(range(len(points_gdf)))]
#        split = [points_gdf.iloc[[i]] for i in tqdm.tqdm(range(10))] ## DEBUGGING ##
##        num_cores = multiprocessing.cpu_count() - 2
#        num_cores = 1
#        # Run spatial joins in parallel to get counts
#        logging.info('Performing spatial join on each feature in AOI...')
#        results = Parallel(n_jobs=num_cores)(delayed(get_count_indexed)(i, fp_sel) for i in tqdm.tqdm(split))
#        # Combine individual gdfs back into one
#        density_results = pd.concat(results)
#    except Exception as e:
#        print(e)
#    
#    ## Write grid out
#    if write_path:
#        driver = 'ESRI Shapefile'
#        try:
#            density_results.to_file(write_path, driver=driver)
#        except Exception as e:
#            print(e)
#    return density_results
    

def rasterize_grid(grid_path, count_field):
    '''
    Takes a point shapefile and rasterizes based on 'count' field, need to better
    create raster grid size (hardcoded at 1000 units of project)
    '''
    ## Rasterize
    dir_name = os.path.dirname(grid_path)
    out_name = os.path.basename(grid_path).split(',')[0]
    out_path = os.path.join(dir_name, '{}_rasterize.tif'.format(out_name))
    
    gdal_bin = r"C:\OSGeo4W64\bin"
    gdal_grid = os.path.join(gdal_bin, 'gdal_grid.exe')
    command = '''{} -zfield "count" -a nearest -outsize 1000 1000 -ot UInt16 -of GTiff -l {} {} {}'''.format(gdal_grid, out_name, grid_path, out_path)
    
    run_subprocess(command)
    