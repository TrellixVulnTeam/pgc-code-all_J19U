# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:05:51 2019

@author: disbr007
"""

import fiona
from shapely.geometry import Point, shape, mapping
import geopandas as gpd
import pandas as pd
import numpy as np
import tqdm, subprocess, os, time, logging

import multiprocessing
from joblib import Parallel, delayed

from query_danco import query_footprint
from get_bounding_box import get_bounding_box

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
#    logger.DEBUG('Output: {}'.format(output))
#    logger.DEBUG('Err: {}'.format(error))
    

## Set up logging
logger = logging.getLogger()

formatter = '%(asctime)s -- %(levelname)s: %(message)s'
logging.basicConfig(filename=r'E:\disbr007\scratch\fp_density.log', 
                    filemode='w', 
                    format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.DEBUG)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter('%(asctime)s -- %(levelname)s: %(message)s')
logger.addHandler(lso)

logger.info('Starting density calculation...')

# Name of output files
out_name = r'arctic2'


## Create point grid over aoi polygon - assuming only one feature
# Read in boundary polygon
boundary_path = r'E:\disbr007\scratch\arctic_dissolve.shp'
with fiona.open(boundary_path, 'r') as ds_in:
    crs = ds_in.crs
    # Determine bounds
#    minx, miny, maxx, maxy = get_bounding_box(boundary_path)
    minx, miny, maxx, maxy = -0.01, 60.001, 180.01, 90.001
    range_x = (maxx - minx)
    range_y = (maxy - miny)
    
# Set number of rows and cols for grid
step = 100

# Determine spacing of points in units of polygon projection (xrange / step)
x_space = range_x / step
y_space = range_y / step

# Create points (loop over number cols, inner loop number rows), add to list of gdfs of points
x = minx
y = miny
points = []
cols = ['count', 'geometry']
for x_step in np.arange(minx, maxx+x_space, x_space):
    y = miny
    for y_step in np.arange(miny, maxy+y_space, y_space):
        the_point = Point(x,y)
        points.append(the_point)
        y += y_space
    x += x_space

# Put points into geodataframe with empty 'count' column for storing count of overlapping fps
cols = ['count', 'geometry']
density_gdf = gpd.GeoDataFrame(columns=cols)
density_gdf.crs = crs
density_gdf['geometry'] = points


## Count number of polygons over each point
# Read in footprint to use
driver = 'ESRI Shapefile'
fp = query_footprint(layer='dg_imagery_index_stereo_cc20')

# Do initial join to get all intersecting
logger.info('Performing initial spatial join.')
# Check projections are the same, if not reproject
if fp.crs != density_gdf.crs:
    fp = fp.to_crs(density_gdf.crs)
fp_sel = gpd.sjoin(fp, density_gdf, how='inner', op='intersects')
fp_sel.drop(columns=['index_right'], inplace=True)
del fp


logger.info('Performing spatial join for each feature to obtain counts.')
## For each point in grid count overlaps
# Split grid into individual gdfs
split = [density_gdf.loc[[i]] for i in tqdm.tqdm(range(len(density_gdf)))]
num_cores = multiprocessing.cpu_count() - 2
# Run spatial joins in parallel to get counts
results = Parallel(n_jobs=num_cores)(delayed(get_count)(i, fp_sel) for i in tqdm.tqdm(split))
# Combine individual gdfs back into one
density_results = pd.concat(results)

## Write grid out
grid_path = os.path.join(r'E:\disbr007\scratch', '{}.shp'.format(out_name))
density_results.to_file(grid_path, driver=driver)

## Rasterize
layer_name = out_name
grid = grid_path
out_path = os.path.join(r'E:\disbr007\scratch', '{}_rasterize.tif'.format(out_name))
gdal_bin = r"C:\OSGeo4W64\bin"
gdal_grid = os.path.join(gdal_bin, 'gdal_grid.exe')
command = '''{} -zfield "count" -a nearest -outsize 1000 1000 -ot UInt16 -of GTiff -l {} {} {}'''.format(gdal_grid, layer_name, grid, out_path)

run_subprocess(command)