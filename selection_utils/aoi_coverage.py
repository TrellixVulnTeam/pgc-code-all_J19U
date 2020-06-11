# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 13:42:10 2020

@author: disbr007
"""
import numpy as np

import geopandas as gpd
import pandas as pd

from archive_analysis.archive_analysis_utils import grid_aoi, get_count
from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'DEBUG')


aoi_path = r'V:\pgc\data\scratch\jeff\deliverables\4218_schild_thwaites_dems\SarahChild_Jun1_data_request.shp'
fps_path = r'V:\pgc\data\scratch\jeff\deliverables\4218_schild_thwaites_dems\schild_2020jun03_request_init_selection.shp'
n_pts_x = 100
n_pts_y = 100
fps_id = 'pairname'
cov_thresh = 10
cover_all = True


def cover_feature(feat_fps, feat_grid, cov_thresh=0,
                  pt_id='pt_id', pt_count='pt_count',
                  pts_covered='pts_covered', coverd='covered',
                  perc_covered='perc_covered', keep='keep'):
    
    the_fps = []
    covered_perc = 0
    for i, row in feat_fps.iterrows():
        fp_pts = row[pts_covered]
        # logger.debug('Footprint points covered: {}'.format(row[pt_count]))
        added_coverage = (((np.count_nonzero(np.where(feat_grid[covered] != True,
                                                      feat_grid[pt_id].isin(fp_pts),
                                                      feat_grid[covered]))) / len(feat_grid)) - covered_perc) * 100
        added_coverage = (((np.count_nonzero(np.where(feat_grid[covered] != True,
                                                      feat_grid[pt_id].isin(fp_pts),
                                                      feat_grid[covered]))) / len(feat_grid)) - covered_perc) * 100
        # logger.debug('Added coverage: {:.2f}'.format(added_coverage))
        
        # Update any False values in the 'covered' field if they are covered by the footprint
        logger.debug(added_coverage)
        logger.debug(cov_thresh)
        if added_coverage >= cov_thresh:
            # logger.debug('Adding footprint...')
            feat_grid[covered] = np.where(feat_grid[covered] != True,
                                          feat_grid[pt_id].isin(fp_pts), 
                                          feat_grid[covered])
            the_fps.append(row[fps_id])
        else:
            # logger.debug('Skipping footprint...')
            pass
        # logger.debug('Points covered: {}'.format(len(feat_grid[feat_grid[covered]==True])))
        
        # covered_perc = len(feat_grid[feat_grid[covered]==True]) / len(feat_grid)
        # logger.debug('Percent covered: {:.2f}'.format(covered_perc))
    
    return the_fps
    
# Params
pt_id = 'pt_id' # index name for grids
pt_count = 'pt_count'
pts_covered = 'pts_covered'
covered = 'covered'
perc_covered = 'perc_covered'
keep = 'keep'

# Load
aoi = gpd.read_file(aoi_path)
fps = gpd.read_file(fps_path)
fps[keep] = False

if fps.crs != aoi.crs:
    fps = fps.to_crs(aoi.crs)

keep_fps = []
for i, row in aoi.iterrows():
    logger.debug('Finding footprints over AOI: {}'.format(i))
    # Create a grid over the current AOI
    grid_points_covered = []
    feat_grid = grid_aoi(row.geometry, n_pts_x=n_pts_x, n_pts_y=n_pts_y, aoi_crs=aoi.crs)
    feat_grid.index.names = [pt_id]
    feat_grid.reset_index(inplace=True)
    # feat_grid[covered] = False
    
    # Select footprints over the current AOI
    feat_fps = fps[fps.geometry.intersects(row.geometry)]
    # feat_fps[keep] = False
    
    # Spatial join to determine how many and which grid points covered by each footprint
    sj = gpd.sjoin(feat_fps, feat_grid)
    gb = sj.groupby(fps_id).agg(pt_count=(pt_id, 'count'),
                                pts_covered=(pt_id, 'unique'))
    feat_fps = pd.merge(feat_fps, gb, left_on=fps_id, right_on=fps_id)
    feat_fps.sort_values(by=pt_count, inplace=True, ascending=False)
    
    # Iterate through footprints keeping the footprint that covers the most grid points
    for i, row in feat_fps.iterrows():
        # Decide whether to keep current footprint based on added coverage
        fp_pts = row[pts_covered]
        new_pts = [pt for pt in fp_pts if pt not in grid_points_covered]
        added_coverage = (len(new_pts) / len(feat_grid)) * 100
        
        if added_coverage >= cov_thresh:
            # Save the footprint IDs
            keep_fps.append(row[fps_id])
            # Save the points that the footprint covered
            grid_points_covered.extend(fp_pts)

    if cover_all:
        # Remove already kept pts from pts covered list for each fp
        # feat_fps[pts_covered] = feat_fps[pts_covered].apply(lambda x: [pt for pt in x if pt not in grid_points_covered])
        # # Sort by number of remaining points covered
        # feat_fps[pt_count] = feat_fps[pts_covered].apply(lambda x: len(x))
        # feat_fps.sort_values(by=pt_count, inplace=True)
        
        ## Create a seperate dataframe that is updated while iterating through fps, storing points 
        ## that were added during cover_all, that can be then checked against to see if anything new 
        ## is covered by the new footprint.
        
        for i, row in feat_fps.iterrows():
            # Decide whether to keep current footprint based on added coverage
            fp_pts = row[pts_covered]
            new_pts = [pt for pt in fp_pts if pt not in grid_points_covered]
            added_coverage = (len(new_pts) / len(feat_grid)) * 100
            
            if added_coverage > 0:
                logger.debug("New pts: {}".format(len(new_pts)))
                # Save the footprint IDs
                keep_fps.append(row[fps_id])
                # Save the points that the footprint covered
                grid_points_covered.extend(new_pts)


fps[keep] = np.where(fps[fps_id].isin(keep_fps), True, fps[keep])
logger.debug(len(fps[fps[keep]==True]))

# Select the footprint(s) with most coverage until all points covered
# (only select footprint if it covers x% more of AOI)
# (secondary sorting criteria - if within range of %, but x higher criteria, choose instead)

#%%
# import matplotlib.pyplot as plt
# plt.style.use('spy4_blank')

# fig, ax = plt.subplots(1,1)
# fps[fps[keep]==True].plot(color='white', alpha=0.5, ax=ax)
# aoi.plot(color='none', edgecolor='red', ax=ax)