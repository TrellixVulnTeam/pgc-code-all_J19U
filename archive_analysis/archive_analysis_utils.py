# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:05:51 2019

@author: disbr007
"""
import subprocess, os
from copy import deepcopy
import numpy as np
import multiprocessing
from datetime import datetime as dt
#from joblib import Parallel, delayed

from tqdm import tqdm
import fiona
from shapely.geometry import Point, Polygon, box
import geopandas as gpd
import pandas as pd

from selection_utils.query_danco import query_footprint
# from misc_utils.get_bounding_box import get_bounding_box
# from range_creation import range_tuples
from misc_utils.logging_utils import create_logger

## Set up logger
logger = create_logger(__name__, 'sh', 'INFO')


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()


def grid_aoi(aoi_path, n_pts_x=None, n_pts_y=None,
             x_space=None, y_space=None, aoi_crs=None,
             poly=False):
    # Read in AOI - assumes only one feature
    logger.debug('Creating grid in AOI...')
    if isinstance(aoi_path, gpd.GeoDataFrame):
        aoi_all = aoi_path
    elif isinstance(aoi_path, Polygon):
        aoi_all = gpd.GeoDataFrame(geometry=[aoi_path], crs=aoi_crs)
    else:
        if os.path.exists(aoi_path):
            aoi_all = gpd.read_file(aoi_path)
        else:
            logger.error('Could not locate: {}'.format(aoi_path))

    # Get first feature - should be only feature
    aoi = aoi_all.iloc[:1]

    # Get aoi bounding box
    minx, miny, maxx, maxy = aoi.geometry.bounds.values[0]
    x_range = maxx - minx
    y_range = maxy - miny
    # Determine spacing
    if x_space and y_space:
        logger.debug('Using provided spacing.')
    elif n_pts_x and n_pts_y:
        logger.debug('Determining spacing based on number of points requested.')
        x_space = x_range / n_pts_x
        y_space = y_range / n_pts_y
    logger.debug('Grid spacing\nx: {}\ny: {}'.format(round(x_space, 2), round(y_space, 2)))

    # Create x,y Point geometries
    x_pts = np.arange(minx, maxx, step=x_space)
    y_pts = np.arange(miny, maxy, step=y_space)
    mesh = np.array(np.meshgrid(x_pts, y_pts))
    xys = mesh.T.reshape(-1, 2)
    grid_points = [Point(x, y) for (x, y) in xys]

    # Make geodataframe of Point geometries
    grid = gpd.GeoDataFrame(geometry=grid_points, crs=aoi.crs)

    # Remove any grid points that do not fall in actual feature aoi_all
    grid['in'] = [pt.within(aoi.geometry.iloc[0]) for pt in grid.geometry]

    grid = grid[grid['in'] == True].drop(columns=['in'])

    if poly:
        logger.debug('Creating polygon grid...')
        x_pts = sorted(set(grid.geometry.values.x))
        y_pts = sorted(set(grid.geometry.values.y))

        all_cells = []
        for i, x in tqdm(enumerate(x_pts), total=len(x_pts)):
            if i == len(x_pts) - 1:
                break
            next_x = x_pts[i + 1]
            for j, y in enumerate(y_pts):
                if j == len(y_pts) - 1:
                    break
                next_y = y_pts[j + 1]
                cell = box(x, y, next_x, next_y)
                all_cells.append(cell)
        grid = gpd.GeoDataFrame(geometry=all_cells, crs=grid.crs)

    return grid


# def grid_aoi(aoi_shp, step=None, x_space=None, y_space=None, write=False):
#     '''
#     Create a grid of points over an AOI shapefile. Only one of 'step' or 'x_space' and 'y_space'
#     should be provided.
#     aoi_shp: path to shapefile of AOI - must be only one feature -> can be MultiPolygon
#     step: number of rows and columns desired in output grid
#     x_space: horizontal spacing in units of aoi_shp projection
#     y_space: vertical spacing in units of aoi_shp projection
#     '''
#     logger.info('Creating grid in AOI...')
#     if isinstance(aoi_shp, gpd.GeoDataFrame):
#         boundary = aoi_shp
#     else:
#         if os.path.exists(aoi_shp):
#             boundary = gpd.read_file(aoi_shp)
#         else:
#             logger.error('Could not locate: {}'.format(aoi_shp))
    
#     # with fiona.open(aoi_shp, 'r') as ds_in:
#     #     crs = ds_in.crs
#     crs = boundary.crs
#     # Determine bounds
#     # minx, miny, maxx, maxy = get_bounding_box(aoi_shp)
#     minx, miny, maxx, maxy = boundary.total_bounds
#     range_x = (maxx - minx)
#     range_y = (maxy - miny)
        
#     # Set number of rows and cols for grid
#     if step:
#         # Determine spacing of points in units of polygon projection (xrange / step)
#         x_space = range_x / step
#         y_space = range_y / step
    
#     # Create points (loop over number cols, inner loop number rows), add to list of gdfs of points
#     x = minx
#     y = miny
#     points = []
#     logger.info('Creating grid points...')
#     for x_step in tqdm(np.arange(minx, maxx+x_space, x_space)):
#         y = miny
#         for y_step in np.arange(miny, maxy+y_space, y_space):
#             # print('{:.2f}, {:.2f}'.format(x, y))
#             the_point = Point(x,y)
#             if the_point.intersects(boundary.geometry[0]):
#                 points.append(the_point)
#             y += y_space
#         x += x_space
    
#     # Put points into geodataframe
#     col_names = ['geometry']
#     points_gdf = gpd.GeoDataFrame(columns=col_names)
#     points_gdf.crs = crs
#     points_gdf['geometry'] = points
#     if write:
#         out_dir = os.path.dirname(aoi_shp)
#         out_name = '{}_grid.shp'.format(os.path.basename(aoi_shp).split('.')[0])
#         out_path = os.path.join(out_dir, out_name)
#         points_gdf.to_file(out_path)

#     return points_gdf


def get_count(geocells, fps, date_col=None):
    '''
    Gets the count of features in fps that intersect with each feature in geocells
    This method is essentially a many to many spatial join, so if two footprints
    overlaps a grid cell, there will be two of that grid cell in the resulting
    dataframe. These repeated cells are then counted and saved to the returned
    dataframe
    
    geocells: geodataframe of features to count within
    fps: geodataframe of polygons
    '''
    ## Confirm crs is the same
    logger.info('Counting footprints over each feature...')
    if geocells.crs != fps.crs:
        logger.info('Converting crs of grid to match footprint...')
        geocells = geocells.to_crs(fps.crs)

    # TODO: Speed the subsequent spatial join by first intersecting
    logger.info('Performing spatial join...')
    ## Get a column from fps to use to test if sjoin found matches
    fp_col = fps.columns[0]
    sj = gpd.sjoin(geocells, fps, how='left', op='intersects')
    sj.index.names = ['count']
    sj.reset_index(inplace=True)
    
    logger.info('Getting count...')
    ## Remove no matches, group the rest, counting the index, and
    ## get minimum and maximum dates if requested
    agg = {'count':'count'}
    if date_col:
        agg[date_col] = ['min', 'max']
        
    gb = sj[~sj[fp_col].isna()].groupby('count').agg(agg)
    ## Join geocells to dataframe with counts
    out = geocells.join(gb)

    out = gpd.GeoDataFrame(out, geometry=out.geometry, crs=geocells.crs)

    return out


def get_time_range(pts, fps, fps_date_col, keep_datetime=False):
    '''
    Gets the earliest, latest, and range of dates over
    each point that are present in fps
    pts: geodataframe of points of interest
    fps: geodataframe of footprints
    fps_date_col: name of date column in fps
    '''
    def col_strftime(date_col):
        str_date = date_col.dt.strftime('%Y-%m-%d')
        return str_date
    
    if type(fps[fps_date_col]) != pd._libs.tslibs.timestamps.Timestamp:
        fps[fps_date_col] = pd.to_datetime(fps[fps_date_col])
        
    
    ## Confirm crs is the same
    if pts.crs != fps.crs:
        logger.info('Converting crs of grid to match footprint...')
        fps = fps.to_crs(fps.crs)
        
    logger.info('Performing spatial join...')
    ## Get a column from fps to use to test if sjoin found matches
    fp_col = fps.columns[1]
    sj = gpd.sjoin(pts, fps, how='left', op='intersects')
    ## Create index to groupyby and join on later
    sj.index.names = ['idx']
    sj.reset_index(inplace=True)
    
    ## Remove no matches, group the rest, counting the index
    gb = sj[~sj[fp_col].isna()].groupby('idx').agg({fps_date_col:['min', 'max']})
    
    ## Join geocells to dataframe with counts
    out = pts.join(gb)
    out.rename(columns={(fps_date_col, 'max'): 'date_max', (fps_date_col, 'min'): 'date_min'}, inplace=True)
    out['months_range'] = ((out['date_max'] - out['date_min'] ) / np.timedelta64(1, 'M')).astype(int)
    
    if keep_datetime == False:
        datetime_cols = out.select_dtypes(include=['datetime']).columns
        for dc in datetime_cols:
            out[dc] = out[dc].dt.strftime('%Y-%m-%d')
    out = gpd.GeoDataFrame(out, geometry='geometry', crs=fps.crs) 

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



# def get_density(footprint, points_gdf, write_path=False):
#    '''
#    Gets the overlap count over each point in points geodataframe.
#    footprint: danco footprint layer name
#    points: geodataframe of points
#    '''
#    ## Count number of polygons over each point
#    # Read in footprint to use
#    fp = query_footprint(layer=footprint, columns=['catalogid', 'x1', 'y1'])

#    ## Do initial join to get all intersecting
#    logger.info('Performing initial spatial join with entire AOI...')
#    # Check projections are the same, if not reproject
#    if fp.crs != points_gdf.crs:
#        fp = fp.to_crs(points_gdf.crs)
#    # Perform spatial join
#    fp_sel = gpd.sjoin(fp, points_gdf, how='inner', op='intersects')
# #    fp_sel = gpd.overlay(fp, points_gdf, how='intersection')
#    # Not sure why there are duplicate footprints but there are... 
#    fp_sel.drop_duplicates(subset=['catalogid'], keep='first', inplace=True)
#    fp_sel.drop(columns=['index_right'], inplace=True)

#    del fp
   
#    ## For each point in grid count overlaps
#    # Split grid into individual gdfs
#    logger.info('Splitting AOI into individual features for parallel processing...')
#    try:
# #        split = [points_gdf.iloc[[i]] for i in tqdm.tqdm(range(len(points_gdf)))]
#        split = [points_gdf.iloc[[i]] for i in tqdm.tqdm(range(10))] ## DEBUGGING ##
# #        num_cores = multiprocessing.cpu_count() - 2
#        num_cores = 1
#        # Run spatial joins in parallel to get counts
#        logger.info('Performing spatial join on each feature in AOI...')
#        results = Parallel(n_jobs=num_cores)(delayed(get_count_indexed)(i, fp_sel) for i in tqdm.tqdm(split))
#        # Combine individual gdfs back into one
#        density_results = pd.concat(results)
#    except Exception as e:
#        print(e)
   
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
    Takes a point shapefile and rasterizes based on count_field
    TODO: Need to better create raster grid size 
          (hardcoded at 1000 units of project)
          Can we measure the distance betweens points in
          units of projection.
    '''
    ## Rasterize
    dir_name = os.path.dirname(grid_path)
    out_name = os.path.basename(grid_path).split(',')[0]
    out_path = os.path.join(dir_name, '{}_rasterize.tif'.format(out_name))
    
    gdal_bin = r"C:\OSGeo4W64\bin"
    gdal_grid = os.path.join(gdal_bin, 'gdal_grid.exe')
    command = '''{} -zfield "count" -a nearest -outsize 1000 1000 -ot UInt16 -of GTiff -l {} {} {}'''.format(gdal_grid, out_name, grid_path, out_path)
    
    run_subprocess(command)
    