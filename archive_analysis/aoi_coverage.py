# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 09:46:58 2020

@author: disbr007
"""

import os
import logging.config
import numpy as np
from tqdm import tqdm

import geopandas as gpd

from archive_analysis.grid_aoi import grid_aoi
from misc_utils.logging_utils import LOGGING_CONFIG


# Use footprint that covers most points? -- break down acqdate into year or year-month, sort by that
# then sort by most points
# Min AOI area covered (for small AOIs)?
# TODO: Drop any grid points that are not covered by input footprint and warn, but at list this 
#       will prevent unneccessary looping of footprints when no new points will be covered

#### Inputs
aoi_path = r'V:\pgc\data\scratch\jeff\deliverables\schild_temp\SarahChild_2_13_20_data_request.shp'
# or danco DB (add danco suport later)
fps_path = r'V:\pgc\data\scratch\jeff\deliverables\schild_temp\pgc_dem_setsm_strips_selection.shp'
danco_fp = r''
depth = 1 # number of repeats
min_fps = False # Find footprints that cover most area
init_check = True # Perform initial check to ensure footprints cover AOI, warn if not
x_space = 1000 # in units of AOI, lower = more grid points and longer inital creation time
y_space = 1000 # in units of AOI
step = None # number of rows and columns to grid with
plot = True

# Logging set up
handler_level = 'DEBUG'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


#### Parameters
sort_crit = 'acqdate1'
sort_crit_ascending = False # newest first
# Field names
covered_depth = 'covered_depth' # field in grid to store depth of coverage
pt_id = 'pt_id'
fp_id = 'pairname' # name of field in footprint that is unique to each footprint


#### Load data
# AOI
aoi = gpd.read_file(aoi_path)
# Footprint
fps = gpd.read_file(fps_path)


# Check for crs match
if fps.crs != aoi.crs:
    logger.debug('CRS mismatch, converting footprints crs...')
    fps = fps.to_crs(aoi.crs)

# testing only - subset to larger strips only
fps = fps[fps.area/1e6 > 1000]    
# testing only - subset to higher density only
fps = fps[fps['density'] > 0.80]

#### For each polygon, create grid as geodataframe, add to list
aoi_grids = []
# Loop over polygons
logger.info('Creating a grid for each polygon in AOI ({})'.format(len(aoi)))
for poly_idx in aoi.index.unique():
    poly = aoi[aoi.index == poly_idx]

    # Grid polygon
    grid = grid_aoi(poly, x_space=x_space, y_space=y_space, step=step)
    # Add unique ID field
    grid[pt_id] = [x for x in range(len(grid))]
    
    if init_check:
        logger.info('Performing initial check to ensure footprints supplied cover entire AOI...')
        precheck_len = len(grid)
        grid_cols = list(grid)
        # Drop any grid points that do not intersect any footprints
        grid = gpd.sjoin(grid, fps, how='inner')
        grid.drop_duplicates(subset=pt_id, inplace = True)
        grid = grid[grid_cols]
        postcheck_len = len(grid)
        if precheck_len != postcheck_len:
            logger.warning('Supplied footprint does not cover entire AOI...')
            logger.warning('Percent covered by all footprints ~ {:.2f}%'.format((postcheck_len/precheck_len)*100))
            logger.warning('Using this subset area only...')
    
    # Add field to store number of footprints over each point
    grid[covered_depth] = 0


    # Add to list
    aoi_grids.append(grid)


#### For each grid, for each point,
# En masse, via sjoin:
# -sort by sort criteria
# -find all points that footprint covers
# -field 'covered' += 1 for those points
# While a point['covered'] < depth, continue until no more footprints
logger.info('Covering each grid point for each AOI, starting with "{}", ascend={}'.format(sort_crit, sort_crit_ascending))
for grid in aoi_grids:
    # Get all footprints that intersect each grid point
    # this results in a repeat of each grid point for 
    # each footprint that intersects it.
    logger.debug('Performing spatial join of grid to all footprints...')
    all_matches = gpd.sjoin(grid, fps, how='left')
    # Create a seperate dataframe with a row for each footprint and 
    # a list of all the grid points that intersect it.
    am_group = all_matches.groupby(fp_id).agg(pts=(pt_id,'unique'),
                                              sort=(sort_crit, 'first'))
    am_group.reset_index(inplace=True)
    # Sort footprints by sort criteria
    am_group.sort_values(by='sort', ascending=sort_crit_ascending, inplace=True)
    # all_matches.sort_values(by=sort_crit, ascending=sort_crit_ascending, inplace=True)
    ## Iterate through each footprint counting each time a grid point is covered, until
    ## are grid points are covered to desired depth
    # Store footprints to keep in a list
    keep_fp_ids = []
    # Set grid index to unique point ID for updating covered depths
    all_covered = False
    # subset matches for testing
    # all_matches = all_matches[0:5000]
    # for i, row in tqdm(all_matches.iterrows(), total=len(all_matches)):
    logger.info('Finding footprints that cover AOI...')
    for i, row in tqdm(am_group.iterrows(), total=len(am_group)):
        # while all_covered == False:
        # Get a list of all the points covered by the current footprint
        pts_covered = am_group[am_group[fp_id]==row[fp_id]]['pts'].tolist()
        # If footprint does not cover any points, skip it
        if len(pts_covered) == 0:
            continue
        else:
            pts_covered = pts_covered[0]
        # Check to see if any of the points covered by this point have not reached depth yet
        # if so, keep them
        new_pts = np.array(grid[grid[pt_id].isin(pts_covered)][covered_depth] < depth).any()
        if new_pts == False:
            continue
        # Add one to the depth count of each of those points
        grid.loc[grid[pt_id].isin(pts_covered), covered_depth] = grid.loc[grid[pt_id].isin(pts_covered), covered_depth] + 1
        # Save the id of the current footprint
        keep_fp_ids.append(row[fp_id])
        # Check if all points have been covered to desired depth
        all_covered = np.array(grid[covered_depth] >= depth).all()
        if all_covered == True:
            break

# Check if all points were covered, warn if not
if all_covered == True:
    logger.info('Entire AOI covered at given grid spacing.')
else:
    logger.warning('Entire AOI not covered...')
    logger.warning('AOI coverage: {}%'.format((len(grid[grid[covered_depth] >= depth])/len(grid))*100))


# Get all footprints to keep
keep_fps = fps[fps[fp_id].isin(keep_fp_ids)]


#### Print summary of sort criteria (min, max, mean)
# logger.info('Summary of selected footprints:\n {}'.format(keep_fps.describe()))
logger.info('Footprints selected: {}'.format(len(keep_fps)))
logger.info('Minimum sort criteria: {}'.format(keep_fps[sort_crit].min()))

if plot:
    import matplotlib.pyplot as plt
    plt.style.use('ggplot')
    fig, ax = plt.subplots(1,1, figsize=(10,10))
    aoi.boundary.plot(edgecolor='r', ax=ax)
    grid.plot(ax=ax, column=covered_depth, markersize=10)
    keep_fps.plot(ax=ax, linewidth=0.8, edgecolor='black', alpha=0.5)
