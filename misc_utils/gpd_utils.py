# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 11:30:25 2019

@author: disbr007
"""

import geopandas as gpd
from shapely.geometry import Point, LineString
from shapely.ops import split
import matplotlib.pyplot as plt
import copy


def multiline_split(polygon, split_lines):
    split_polygons = []
    remains = copy.deepcopy(p)
    for i, ln in enumerate(split_lines):
        chopped = list(split(remains, ln))
        keep = chopped[0]
        remains = chopped[1]
        split_polygons.append(keep)
        if i == (len(splt_lns)-1):
            split_polygons.append(remains)
    
    return split_polygons


def grid_poly(poly, cells):
    '''
    split a polygon into the given number of equal area cells
    poly: gdf of polygons to split
    cells: number of cells per polygon
    '''
 

    return poly

driver = 'ESRI Shapefile'
geocells_path = r'E:\disbr007\scratch\geocells_sub_single.shp'

## Function inputs
poly = gpd.read_file(geocells_path, driver=driver)
nrows = 4
ncols = 2

## Function begins
# Determine how many points along boundary are needed - how many split lines
num_row_split_pts = nrows - 1
num_col_split_pts = ncols - 1

# Get polygon geometries as list
polys = list(poly.geometry) 

# For each polygon create app number of points along the boundary
for p in polys:
    minx, miny, maxx, maxy = p.bounds
    top = LineString([(minx, maxy), (maxx, maxy)])
#    bottom = LineString([(minx, miny), (maxx, miny)])
    left = LineString([(minx, miny), (minx, maxy)])
#    right = LineString([(maxx, miny), (maxx, maxy)])
#    bound_lines = [top, bottom, left, right]
    
    ## Cell geoms
    final_cell_polys = []
    
    ## Make vertical split lines
    splt_lns = []
    length = top.length
    step = length / nrows
    dist = 0
    for n in range(num_row_split_pts):
        dist += step
        top_pt = top.interpolate(dist)
        bot_pt = Point(top_pt.x, miny)
        ln = LineString([top_pt, bot_pt])
        splt_lns.append(ln)
          
#    remains = copy.deepcopy(p)    
#    for i, ln in enumerate(splt_lns):
#        chopped = list(split(remains, ln))
#        keep = chopped[0]
#        remains = chopped[1]
#        cell_polys.append(keep)
#        if i == (len(splt_lns)-1):
#            cell_polys.append(remains)
        
    ## Make horizontal split lines
    length = left.length
    step = length / ncols
    dist = 0
    for n in range(num_col_split_pts):
        dist += step
        left_pt = left.interpolate(dist)
        right_pt = Point(maxx, left_pt.y)
        ln = LineString([left_pt, right_pt])
        splt_lns.append(ln)


#lines_gdf = gpd.GeoDataFrame(geometry=bound_lines)    
#pts_gdf = gpd.GeoDataFrame(geometry=splt_lns)
#chopped_gdf = gpd.GeoDataFrame(geometry=chopped)
cells_gdf = gpd.GeoDataFrame(geometry=final_cell_polys)
#remains_gdf = gpd.GeoDataFrame(geometry=[remains])

## Plot for testing
# Plot data
fig, ax = plt.subplots(1,1)
#chopped_gdf.plot(color='', edgecolor='green', ax=ax)
#chopped_gdf.iloc[[0]].plot(color='black', ax=ax)
cells_gdf.plot(color='grey', edgecolor='black', ax=ax)
#remains_gdf.plot(color='red', edgecolor='white', ax=ax)
#lines_gdf.plot(color='red', ax=ax)
#pts_gdf.plot(color='blue', ax=ax)

#    cell_grid.plot(ax=ax, color='red')

# Adjust figure
minx, miny, maxx, maxy = arc_cells.total_bounds
xstep = (maxx - minx) / 10
ystep = (maxy- miny) / 10
ax.set_xlim(minx-xstep, maxx+xstep)
ax.set_ylim(miny-ystep, maxy+ystep)
plt.show()

