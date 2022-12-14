# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 11:30:25 2019

@author: disbr007
"""
import matplotlib.pyplot as plt
import copy, logging, os
import numpy as np
import random
import pathlib
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import split
from scipy.sparse.csgraph import connected_components
from tqdm import tqdm

import multiprocessing

from misc_utils.logging_utils import create_logger
from misc_utils.gdal_tools import detect_ogr_driver

logger = create_logger(__name__, 'sh', 'DEBUG')

# CONSTANTS
# Drivers
ESRI_SHAPEFILE = 'ESRI Shapefile'
GEOJSON = 'GeoJSON'
GPKG = 'GPKG'
OPEN_FILE_GDB = 'OpenFileGDB'
FILE_GBD = 'FileGDB'


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


def remove_unused_geometries(df):
    """
    Remove all geometry columns that aren't being used. Useful for
    writing to shapefiles
    """
    remove = [x for x in list(df.select_dtypes(include='geometry'))
              if x != df.geometry.name]

    return df.drop(columns=remove)


def select_in_aoi(gdf, aoi, centroid=False):
    gdf_cols = list(gdf)
    logger.debug('Making selection over AOI')
    if aoi.crs != gdf.crs:
        aoi = aoi.to_crs(gdf.crs)
    if centroid:
        logger.debug('Using centroid for selection...')
        poly_geom = gdf.geometry
        gdf.geometry = gdf.geometry.centroid
        op = 'within'
    else:
        op = 'intersects'

    gdf = gpd.sjoin(gdf, aoi, op=op)
    # gdf = gpd.overlay(gdf, aoi)
    if centroid:
        gdf.geometry = poly_geom

    # gdf = gdf[gdf_cols]
    # TODO: Confirm if this is needed, does an 'inner' sjoin leave duplicates?
    # gdf.drop_duplicates(subset='pairname')

    return gdf


def dissolve_gdf(gdf):
    dissolve_field = 'dissolve'
    if dissolve_field in list(gdf):
        dissolve_field += random.randint(0, 1000)
    if len(gdf) > 1:
        gdf[dissolve_field] = 1
        gdf = gdf.dissolve(by=dissolve_field)
        gdf = gdf.reset_index()
        gdf = gdf.drop(columns=dissolve_field)

    return gdf


def explode_multi(gdf):
    """
    Will explode the geodataframe's muti-part geometries into single
    geometries. Each row containing a multi-part geometry will be split into
    multiple rows with single geometries, thereby increasing the vertical size
    of the geodataframe. The index of the input geodataframe is no longer
    unique and is replaced with a multi-index.

    The output geodataframe has an index based on two columns (multi-index)
    i.e. 'level_0' (index of input geodataframe) and 'level_1' which is a new
    zero-based index for each single part geometry per multi-part geometry

    Args:
        gdf (gpd.GeoDataFrame) : input geodataframe with multi-geometries

    Returns:
        gdf (gpd.GeoDataFrame) : exploded geodataframe with each single
                                 geometry as a separate entry in the
                                 geodataframe. The GeoDataFrame has a multi-
                                 index set to columns level_0 and level_1
    """
    gs = gdf.explode()
    gdf2 = gs.reset_index().rename(columns={0: 'geometry'})
    gdf_out = gdf2.merge(gdf.drop('geometry', axis=1), left_on='level_0',
                         right_index=True)
    gdf_out = gdf_out.set_index(['level_0', 'level_1']).set_geometry('geometry')
    gdf_out.crs = gdf.crs
    return gdf_out


def datetime2str_df(df, date_format='%Y-%m-%d %H:%M:%S'):
    # Convert datetime columns to str
    date_cols = df.select_dtypes(include=['datetime64']).columns
    for dc in date_cols:
        df[dc] = df[dc].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))


def write_gdf(src_gdf, out_footprint, to_str_cols=None,
              out_format=None,
              date_format=None,
              nan_to=None,
              precision=None,
              overwrite=True,
              **kwargs):
    """
    Handles common issues with writing GeoDataFrames to a variety of formats,
    including removing datetimes, converting list/dict columns to strings,
    handling NaNs.
    date_format : str
        Use to convert datetime fields to string fields, using format provided
    TODO: Add different handling for different formats, e.g. does gpkg allow datetime/NaN?
    """
    gdf = copy.deepcopy(src_gdf)

    if not isinstance(out_footprint, pathlib.PurePath):
        out_footprint = Path(out_footprint)

    # Format agnostic functions
    # Remove if exists and overwrite
    if out_footprint.exists():
        if overwrite:
            logger.warning('Overwriting existing file: '
                           '{}'.format(out_footprint))
            os.remove(out_footprint)
        else:
            logger.warning('Out file exists and overwrite not specified, '
                           'skipping writing.')
            return None

    # Convert datetime if requested
    if date_format:
        if not gdf.select_dtypes(include=['datetime64']).columns.empty:
            datetime2str_df(gdf, date_format=date_format)

    # Round if precision
    if precision:
        gdf = gdf.round(decimals=precision)
    logger.debug('Writing to file: {}'.format(out_footprint))

    # Get driver and layer name. Layer will be none for non database formats
    driver, layer = detect_ogr_driver(out_footprint, name_only=True)
    if driver == ESRI_SHAPEFILE:
        # convert NaNs to empty string
        if nan_to:
            gdf = gdf.replace(np.nan, nan_to, regex=True)

    # Convert columns that store lists to strings
    if to_str_cols:
        for col in to_str_cols:
            logger.debug('Converting to string field: {}'.format(col))
            gdf[col] = [','.join(map(str, l)) if isinstance(l, (dict, list))
                        and len(l) > 0 else '' for l in gdf[col]]

    # Write out in format specified
    if driver in [ESRI_SHAPEFILE, GEOJSON]:
        if driver == GEOJSON:
            if gdf.crs != 4326:
                logger.warning('Attempting to write GeoDataFrame with non-WGS84 '
                               'CRS to GeoJSON. Reprojecting to WGS84.')
                gdf = gdf.to_crs('epsg:4326')
        gdf.to_file(out_footprint, driver=driver, **kwargs)
    elif driver in [GPKG, OPEN_FILE_GDB, FILE_GBD]:
        gdf.to_file(str(out_footprint.parent), layer=layer, driver=driver, **kwargs)
    else:
        logger.error('Unsupported driver: {}'.format(driver))


def dissolve_touching(gdf: gpd.GeoDataFrame):
    dg = 'dissolve_group'

    overlap_matrix = gdf.geometry.apply(
        lambda x: gdf.geometry.touches(x)).values.astype(int)
    n, ids = connected_components(overlap_matrix)
    gdf[dg] = ids

    dissolved = gdf.dissolve(by=dg)

    return dissolved


def read_vec(vec_path: str, **kwargs) -> gpd.GeoDataFrame:
    """
    Read any valid vector format into a GeoDataFrame
    """
    driver, layer = detect_ogr_driver(vec_path, name_only=True)
    if layer is not None:
        gdf = gpd.read_file(Path(vec_path).parent, layer=layer, driver=driver, **kwargs)
    else:
        gdf = gpd.read_file(vec_path, driver=driver, **kwargs)

    return gdf
