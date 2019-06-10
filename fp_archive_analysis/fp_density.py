# -*- coding: utf-8 -*-
"""
Created on Tue May 28 13:05:51 2019

@author: disbr007
"""

import fiona
from shapely.geometry import Point, shape, mapping
import geopandas as gpd
import numpy as np
import tqdm, subprocess, os

from query_danco import query_footprint

out_name = r'ak2'

## Create point grid
# Read in boundary polygon
boundary_path = r'E:\disbr007\scratch\alaska_prj.shp'
with fiona.open(boundary_path, 'r') as ds_in:
    crs = ds_in.crs
    feat = ds_in[0]
    geom = shape(feat['geometry'])
    # Determine bounds
    minx, miny, maxx, maxy = geom.bounds
    range_x = (maxx - minx)
    range_y = (maxy - miny)
    

# Determine step size (# rows and cols)
step = 10

# Determine spacing of points in units of polygon project (xrange / step)
x_space = range_x / step
y_space = range_y / step

# Create points (loop over number cols, inner loop number rows)
x = minx
y = miny
points = []
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
# Read in footprint to use# Write grid out
driver = 'ESRI Shapefile'
#fp_path = r'E:\disbr007\scratch\dg_imagery_index_stereo_cc20_fp.shp'
#fp = gpd.read_file(fp_path, driver=driver)
fp = query_footprint(layer='dg_imagery_index_stereo_cc20')

# Do initial join to get all intersecting
if fp.crs != density_gdf.crs:
    fp = fp.to_crs(density_gdf.crs)
fp_sel = gpd.sjoin(fp, density_gdf, how='inner', op='intersects')
fp_sel.drop(columns=['index_right'], inplace=True)
del fp

# For each point in grid count overlaps
for i in tqdm.tqdm(range(len(density_gdf))): # loop each point in density 'grid'
    feat = density_gdf.loc[[i]] # current feature
    
    # Spatial join for current feature
    sel4feat = gpd.sjoin(fp_sel, feat, how='inner', op='intersects') # select by location
#    print(len(sel4feat))
    # The length of the selection is the count over the current point
    density_gdf.loc[[i], 'count'] = len(sel4feat)

# Write grid out
grid_path = os.path.join(r'E:\disbr007\scratch', '{}.shp'.format(out_name))
density_gdf.to_file(grid_path, driver=driver)

## Rasterize
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    print('Output: {}'.format(output))
    print('Err: {}'.format(error))

layer_name = out_name
grid = grid_path
out_path = os.path.join(r'E:\disbr007\scratch', '{}_rasterize.tif'.format(out_name))
gdal_bin = r"C:\OSGeo4W64\bin"
gdal_grid = os.path.join(gdal_bin, 'gdal_grid.exe')
command = '''{} -zfield "count" -a nearest -outsize 1000 1000 -ot UInt16 -of GTiff -l {} {} {}'''.format(gdal_grid, layer_name, grid, out_path)

run_subprocess(command)