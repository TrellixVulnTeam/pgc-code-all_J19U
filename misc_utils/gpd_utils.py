# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 11:30:25 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import fiona
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import split
import matplotlib.pyplot as plt
import copy, logging, os
from tqdm import tqdm

import multiprocessing
from joblib import Parallel, delayed

logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


def multiprocess_gdf(fxn, gdf, *args, num_cores=None, **kwargs):
    num_cores = num_cores if num_cores else multiprocessing.cpu_count() - 2
    split_dfs = [gdf.iloc[[i]] for i in range(len(gdf))]
    # Run fxn in counts
    results = Parallel(n_jobs=num_cores)(delayed(fxn)(i, *args, **kwargs) for i in tqdm.tqdm(split_dfs))
    # Combine individual gdfs back into one
    output = pd.concat(results)

    return output


def merge_gdf(gdf1, gdf2):
    gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True), crs=gdf1.crs)
    return gdf


def merge_gdfs(gdfs):
    '''merges a list of gdfs'''
    gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
    return gdf


## Function begins
def grid_poly(poly_gdf, nrows, ncols):
    '''
    Takes a geodataframe with Polygon geom and creates a grid of nrows and ncols in its bounding box
    poly: geodataframe with Polygon geometry
    nrows: number of rows in grid
    ncols: numner of cols in grid
    '''
    
    def multiline_split(polygon, split_lines):
        '''
        Split a shapely Polygon by shapely LineStrings
        '''
        base = polygon
        split_polygons = []
        # For each line in split lines (3)
        for i, ln in enumerate(split_lines):
            # Split base at the line, returning two parts
            chopped = list(split(base, ln))
            keep = chopped[0]
            base = chopped[1]
            # Want to keep the smaller area, rechop the bigger, so switch if necessary
            # Output of shapely.ops.split ambiguous in returning smaller or bigger pieces first or second
            if keep.area > base.area:
                keep, base = base, keep
            split_polygons.append(keep)
            if i == len(split_lines)-1:
                split_polygons.append(base)
                break
        return split_polygons


    # Get meta from input gdf
    crs = poly_gdf.crs
    cols = list(poly_gdf)
    cols.remove('geometry')
    
    # Determine how many split lines
    num_row_split_pts = nrows - 1
    num_col_split_pts = ncols - 1
    
    master_gdf = gpd.GeoDataFrame(columns=cols, crs=crs)
    
    for i in tqdm.tqdm(range(len(poly_gdf))):

        feat = poly_gdf.iloc[[i]]

        p = feat.geometry.values[0]

        minx, miny, maxx, maxy = p.bounds
        
        top = LineString([(minx, maxy), (maxx, maxy)])
        left = LineString([(minx, miny), (minx, maxy)])
        
        ## Make vertical split lines
        v_splt_lns = []
        length = top.length
        step = length / nrows
        dist = 0
        for n in range(num_row_split_pts):
            dist += step
            top_pt = top.interpolate(dist)
            bot_pt = Point(top_pt.x, miny)
            ln = LineString([top_pt, bot_pt])
            v_splt_lns.append(ln)
            
        ## Make horizontal split lines
        h_splt_lns = []
        length = left.length
        step = length / ncols
        dist = 0
        for n in range(num_col_split_pts):
            dist += step
            left_pt = left.interpolate(dist)
            right_pt = Point(maxx, left_pt.y)
            ln = LineString([left_pt, right_pt])
            h_splt_lns.append(ln)
        
        ## Cells for each feature
        feat_cells = []
        
        # Split into rows
        intermed_geoms = multiline_split(p, v_splt_lns)
        
        
        # Split into columns
        for g in intermed_geoms:
            cells = multiline_split(g, h_splt_lns)
            for cell in cells:
                feat_cells.append(cell)
                
        # Create gdf of current feature's newly created cells
        feat_gdf = gpd.GeoDataFrame(geometry=feat_cells, crs=crs)
        
        ## Add information from current feature to all newly created cells **SLOW**
        for col in cols:
            feat_gdf[col] = poly_gdf[i:i+1][col].values[0]
        
        # Merge current feature with master
        master_gdf = merge_gdf(master_gdf, feat_gdf)

    return master_gdf


## Function begins
def grid_poly_row(row, nrows, ncols):
    '''
    Takes a geodataframe with Polygon geom and creates a grid of nrows and ncols in its bounding box
    poly: geodataframe with Polygon geometry
    nrows: number of rows in grid
    ncols: numner of cols in grid
    '''
    
    def multiline_split(polygon, split_lines):
        '''
        Split a shapely Polygon by shapely LineStrings
        '''
        base = polygon
        split_polygons = []
        # For each line in split lines (3)
        for i, ln in enumerate(split_lines):
            # Split base at the line, returning two parts
            chopped = list(split(base, ln))
            keep = chopped[0]
            base = chopped[1]
            # Want to keep the smaller area, rechop the bigger, so switch if necessary
            # Output of shapely.ops.split ambiguous in returning smaller or bigger pieces first or second
            if keep.area > base.area:
                keep, base = base, keep
            split_polygons.append(keep)
            if i == len(split_lines)-1:
                split_polygons.append(base)
                break
        return split_polygons


    # Determine how many split lines
    num_row_split_pts = nrows - 1
    num_col_split_pts = ncols - 1
    
    feat = row
    p = feat.geometry
    minx, miny, maxx, maxy = feat.geometry.bounds
    
    top = LineString([(minx, maxy), (maxx, maxy)])
    left = LineString([(minx, miny), (minx, maxy)])
    
    ## Create split lines
    ## vertical split lines
    v_splt_lns = []
    length = top.length
    step = length / nrows
    dist = 0
    for n in range(num_row_split_pts):
        dist += step
        top_pt = top.interpolate(dist)
        bot_pt = Point(top_pt.x, miny)
        ln = LineString([top_pt, bot_pt])
        v_splt_lns.append(ln)
    ## horizontal split lines
    h_splt_lns = []
    length = left.length
    step = length / ncols
    dist = 0
    for n in range(num_col_split_pts):
        dist += step
        left_pt = left.interpolate(dist)
        right_pt = Point(maxx, left_pt.y)
        ln = LineString([left_pt, right_pt])
        h_splt_lns.append(ln)
    
    ## Cells for each feature
    feat_cells = []
    
    # Split into rows
    intermed_geoms = multiline_split(p, v_splt_lns)
    
    
    # Split into columns
    for g in intermed_geoms:
        cells = multiline_split(g, h_splt_lns)
        for cell in cells:
            feat_cells.append(cell)
            
    return feat_cells


#driver = 'ESRI Shapefile'
##geocells_path = r'E:\disbr007\general\geocell\Global_GeoCell_Coverage.shp'
##geocells_path = r'E:\disbr007\scratch\geocells_sub.shp'
#geocells_path = r'E:\disbr007\scratch\antarctic_aoi.shp'
#df = gpd.read_file(geocells_path, driver=driver)
#crs = df.crs
## Results in a list of new geometries for each cell
#tqdm.pandas()
#df['new_geom'] = df.progress_apply(lambda row: grid_poly_row(row, nrows=500, ncols=500), axis=1)
#
## Expands the list of new geometries to unique rows, copying other column data
#all_cells = gpd.GeoDataFrame({col:np.repeat(df[col].values, df['new_geom'].str.len()) for col in df.columns.drop('new_geom')}, crs=crs).assign(**{'new_geom':np.concatenate(df['new_geom'].values)})
## Set the new geometry and drop the old
#all_cells = all_cells.set_geometry('new_geom')
#all_cells.drop(columns=['geometry'], inplace=True)
## Write
#all_cells.to_file(r'E:\disbr007\scratch\ant_aoi_100.shp', driver=driver)


