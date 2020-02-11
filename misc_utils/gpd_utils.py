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

from misc_utils.logging_utils import LOGGING_CONFIG, CustomError


handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def multiprocess_gdf(fxn, gdf, *args, num_cores=None, **kwargs):
    from joblib import Parallel, delayed
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
    Takes a geodataframe with Polygon geom and creates a grid of nrows and ncols 
    in its bounding box
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
    
    for i in tqdm(range(len(poly_gdf))):

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


def coords2gdf(xs, ys, epsg=4326):
    """
    Converts a list of x and y coordinates to a geodataframe
    using the provided epsg code.
    """
    if len(xs) != len(ys):
        logger.error("Coordinate length mismatch:\nX's:'{}, Y's{}".format(len(xs), len(ys)))
        raise CustomError('Coordinate length mismatch.')
        
    gdf = gpd.GeoDataFrame({'ID': [x for x in range(len(xs))]},
                           geometry=[Point(x,y) for x, y in zip(xs, ys)],
                           crs={'init':'epsg:{}'.format(epsg)})
    
    return gdf
