# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 15:11:00 2020

@author: disbr007
Samples values from segmentation polygons with statistics calculated within features of 
interest and outside of features in order to compare values and identify combination of
statistics thresholds to classify.
"""

import logging.config
import os
import random

import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from misc_utils.logging_utils import LOGGING_CONFIG
# from archive_analysis.archive_analysis_utils import grid_aoi


logging.config.dictConfig(LOGGING_CONFIG('DEBUG'))
logger = logging.getLogger(__name__)


def random_points_within(poly, num_pts):
    """
    Generates random points within a polygon

    Parameters
    ----------
    poly : shapely.geometry.Polygon
        Polygon to create features withim.
    num_pts : INT
        Number of points to create.

    Returns
    -------
    LIST : of points within.

    """
    random_pts = []
    
    pt_ctr = 0
    minx, miny, maxx, maxy = poly.bounds
    
    while pt_ctr < num_pts:
        new_pt_x = random.uniform(minx, maxx)
        new_pt_y = random.uniform(miny, maxy)
        new_pt = Point(new_pt_x, new_pt_y)
        
        # If within, keep
        if geom.contains(new_pt):
            random_pts.append(new_pt)
            pt_ctr += 1
    
    return random_pts


def random_points_outside(bounds, polys, num_pts):
    """
    Genereates random points within bounds, but outside of
    polys.
    """
    random_points = []
    
    minx, miny, maxx, maxy = bounds
    
    pt_ctr = 0
    while pt_ctr < num_pts:
        new_pt_x = random.uniform(minx, maxx)
        new_pt_y = random.uniform(miny, maxy)
        new_pt = Point(new_pt_x, new_pt_y)
        
        # If within bounds and not in polys, keep
        in_polys = [p.contains(new_pt) for p in polys]
        if not any(in_polys):
            random_points.append(new_pt)
            pt_ctr += 1
            
    return random_points

    
#### INPUTS
prj_p = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good'
# path to all segments with stats computed
seg_p = os.path.join(prj_p, r'seg\WV02_20150906_clip_ms_lsms_sr5rr200ss400_stats.shp') 
# path to features of interest
feat_p = os.path.join(prj_p, r'shp\digitized_tks_2015.shp')


#### LOAD features
seg = gpd.read_file(seg_p)
feat = gpd.read_file(feat_p)


#### Create random points within each feature
sample_pts = []
for f_idx in feat.index.unique():
    # for debugging
    if f_idx != 1:
        # Get polygon geometry for checking if random point is within
        geom = feat.iloc[f_idx].geometry
        feat_pts = random_points_within(geom, 100)
        sample_pts.extend(feat_pts)


# Create geodataframe of random points
sample = gpd.GeoDataFrame(geometry=sample_pts, crs=feat.crs)

#### Create random points not in features
outside_pts = random_points_outside(seg.total_bounds, list(feat.geometry), 500)
others = gpd.GeoDataFrame(geometry=outside_pts, crs=seg.crs)

# Add column defining inside feature or interest or out
sample['in_feat'] = True
others['in_feat'] = False


#### Spatial join to seg
# Keep only columns of interest
keep_cols = ['tpi31_mean', 'tpi81_mean', 'slope_mean', 'slope_max', 
             'ndvi_mean', 'diffndvi_m', 'diff_mean', 'roughness_',
             'geometry']
seg = seg[keep_cols]

# Combine all points into single dataframe
points = pd.concat([sample, others])
# Get stats for all points
points_stats = gpd.sjoin(points, seg)


#### PLOTTING
plt.style.use('ggplot')
edgecolor = 'w'
plot_cols = ['tpi31_mean', 'tpi81_mean', 'slope_mean', 'slope_max', 
             'ndvi_mean', 'diffndvi_m', 'diff_mean', 'roughness_']

           
fig, axes = plt.subplots(4, 2, figsize=(10,10))
axes = axes.flatten()
for i, col in enumerate(plot_cols):
    ax = axes[i]
    
    points_stats[col].plot.density(ax=ax)
    points_stats[points_stats['in_feat']==True][col].plot.density(ax=ax)
    ax.set_title(col)
    ax.set_ylabel('')
plt.tight_layout()


# points_stats.hist(column='ndvi_mean', ax=ax, bins=20, edgecolor=edgecolor)
# points_stats[points_stats['in_feat']==True].hist(column='ndvi_mean', ax=ax, edgecolor=edgecolor, bins=20, alpha=0.5)
