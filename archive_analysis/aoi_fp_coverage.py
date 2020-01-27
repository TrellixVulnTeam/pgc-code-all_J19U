# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 15:43:57 2019

@author: disbr007
"""
import copy
import os
import logging
import numpy as np

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

from query_danco import query_footprint
from id_parse_utils import write_ids


## Logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)


# Inputs
prj_dir = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056'
aoi_shp_p = os.path.join(prj_dir, 'prj_files', 'BITE_buffers.shp')
aoi_out_path = os.path.join(prj_dir, 'BITE_AHAP_IDs.shp')
ids_out_path = os.path.join(prj_dir, 'AHAP_PHOTO_IDs.txt')

# Alternative to providing danco DB, provide a shapfile of footprints
fps_p = os.path.join(prj_dir, 'BITE_AHAP_selection2020jan14.shp')
db = '' # Danco database (footprint, imagery, etc)
db_tbl = '' # Table name (index_dg, etc)

multi_aoi = True # Does the AOI shapefile have more than one polygon (not implemented yet)
aoi_id = 'id' # Field in AOI that is unique to each polygon
# TODO: Add mfp support
fp_unique_id = 'PHOTO_ID' # Field in footprints layer that is unique to each record
# Other params
step = 500 # spacing of grid points use to check for coverage of AOI, in units of AOI projection
date_field = 'ACC_ACQ_DA' # Date field in footprints, (shapefile, danco DB, or MFP)
cc = 5 # min cloudcover
cc_field = ''
date_min = ''
date_max = ''
where = '' # open ended where clause passed as SQL query to db exactly as typed
load_cols = [] # columns in db_tbl to load, must include any in where clause and date, speeds loading
desired_coverage = 75 # percent of AOI that needs to be covered


# Intermediate outputs for testing
intermed1 = os.path.join(prj_dir, 'int1.shp')
intermed2 = os.path.join(prj_dir, 'int2.shp')


def grid_aoi(aoi_gdf, step):
    """
    Create grid within polygon bounds


    Parameters
    ----------
    aoi_gdf : gpd.GeoDataFrame
        Dataframe of one polygon from AOI.
    step : FLOAT
        distance in units of projection of AOI between coverage-check-points

    Returns
    -------
    pt_grid : gpd.GeoDataFrame
        Dataframe containing grid points.

    """
    # grid_points = []
    for i, row in aoi_gdf.iterrows():
        ## Get feature bounds and geometry
        minx, miny, maxx, maxy = row.geometry.bounds
        g = row.geometry
        ## Create points using boundary locations and step
        pts = []
        for x in np.arange(minx, maxx+step, step):
            for y in np.arange(miny, maxy+step, step):
                pts.append((x,y))
        points = [Point(pt) for pt in pts if (g.contains(Point(pt))) or (g.intersects(Point(pt)))]
        # Add exterior coords to smallest polys (were being skipped??)
        if g.area < step*step:
            first_ext_pt = Point(g.exterior.coords[0])
            midd_ext_pt = Point(g.exterior.coords[round(len(g.exterior.coords)/2)])
            points.extend([first_ext_pt, midd_ext_pt])
        # grid_points.extend(points)

    pt_grid = gpd.GeoDataFrame(geometry=points, crs=aoi_gdf.crs)
    
    return pt_grid


#### Get footprints to start with, if a path is provided use that, else use danco db and tbl
if fps_p:
    fps = gpd.read_file(fps_p)
else:
    fps = query_footprint(db_tbl, db=db, where=where)
# Convert date column to pandas datetime for selecting most recent
fps[date_field] = pd.to_datetime(fps[date_field])


#### Grid input AOI
aoi = gpd.read_file(aoi_shp_p)
aoi = aoi.set_index(aoi_id)
aoi['keep_ids'] = '' # Create column empty to hold the IDs that will be used for each

# Check crs match
if fps.crs != aoi.crs:
    fps = fps.to_crs(aoi.crs)

# Iterate over polygons in AOI, returning grid for each and storing in column in original df
for poly_id in aoi.index.unique():
    poly = aoi[aoi.index==poly_id]
    poly_grid = grid_aoi(poly, step=step)
    # Create indentifying index for each point in the grid
    pt_id = 'pt_id'
    # Create index for points
    poly_grid[pt_id] = [x for x in range(len(poly_grid))]
    # Get all point ids for checking to see if each is covered
    all_pts = list(poly_grid[pt_id])
    poly_grid.set_index(pt_id)
    
    #### Start with most recent and work backwards covering AOI
    ## Find all footprints intersection with points in grid
    print('Finding initial intersection with grid for AOI: {}...'.format(poly_id))
    fps_sel = gpd.sjoin(fps, poly_grid, how='inner')
    fps_sel.sort_values(by=date_field, inplace=True)
    # Remove index columns for next join
    for col in ['index_right', 'index_left']:
        if col in list(fps_sel):
            fps_sel.drop(columns=[col], inplace=True)
    
    # Count how many points are covered by each unique footprint
    fps_count = fps_sel.groupby(fp_unique_id).agg({pt_id: ['nunique', 'unique']})
    # Rename agg columns for clarity
    pt_count = '{}_count'.format(pt_id)
    pts_covered = '{}_covered'.format(pt_id)
    fps_count.columns = fps_count.columns.droplevel(0)
    fps_count = fps_count.rename(columns={'nunique': pt_count, 'unique':  pts_covered})
    # Sort by most points (area) covered
    fps_count.sort_values(by=pt_count, ascending=False, inplace=True)
    ## Determine what points are covered, starting with most coverage, saving unique footprint IDs
    keep_fp_ids = [] # list of footprint IDs to keep    
    percent_covered = 0
    pt_ids_covered = [] # list of all point IDs that are covered
    # Iterate over rows, adding footprint IDs to keep and the pts covered by each until
    # more than the desired coverage is reached
    for row_number in range(len(fps_count)):
        while percent_covered < desired_coverage:
            # Add the points the current row covers (starting with most covered) 
            # to list of all covered
            row = fps_count.iloc[row_number]
            for pt in list(row[pts_covered]):
                if pt not in pt_ids_covered:
                    pt_ids_covered.append(pt)
            keep_fp_ids.append(row.name)
            percent_covered = (len(pt_ids_covered) / len(all_pts))*100
    aoi.at[poly_id, 'keep_ids'] = keep_fp_ids

# Get all footprint IDs to keep, from nested sublists for each AOI
all_ids = [i for sl in list(aoi['keep_ids']) for i in sl]

# Write to file, AOIs with IDs and list of all IDs
# Remove list from cell
aoi['keep_ids'] = aoi['keep_ids'].apply(lambda x: ', '.join([str(e) for e in x]))
aoi.to_file(aoi_out_path)

write_ids(all_ids, ids_out_path)
