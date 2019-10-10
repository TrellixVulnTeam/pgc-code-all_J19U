# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 15:43:57 2019

@author: disbr007
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

from query_danco import query_footprint


## Logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)

aoi_shp = r'E:\disbr007\imagery_orders\nga_special_use_airspace\U.S._Special_Use_Airspace\U.S._Special_Use_Airspace_cea.shp'
cc = 5
date_min = '2017'
#### Create grid within each polygon bounds


def grid_aoi(aoi_shp, step):
    aoi = gpd.read_file(aoi_shp)
    grid_points = []
    for i, row in tqdm(aoi.iterrows()):
        ## Get feature bounds and geometry
        minx, miny, maxx, maxy = row.geometry.bounds
        g = row.geometry
        ## Create points
        step = step #20km
        pts = []
        for x in np.arange(minx, maxx+step, step):
            for y in np.arange(miny, maxy+step, step):
                pts.append((x,y))
        points = [Point(pt) for pt in pts if (g.contains(Point(pt))) or (g.intersects(Point(pt)))]
        # Add exterior coords to smallest polys (were being skipped??)
        if g.area < 300*(1000**2): #300 sqkm
            first_ext_pt = Point(g.exterior.coords[0])
            midd_ext_pt = Point(g.exterior.coords[round(len(g.exterior.coords)/2)])
            points.extend([first_ext_pt, midd_ext_pt])
        grid_points.extend(points)

    pt_grid = gpd.GeoDataFrame(geometry=grid_points, crs=aoi.crs)
    
    return pt_grid


#### Grid input AOI
grid = grid_aoi(aoi_shp, 10*1000)


#### Get all imagery matching specs
#load_cols = ['catalogid', 'acqdate', 'platform', 'cloudcover']
#load_cols = ['acqdate']
## Stereo
#fps = query_footprint('dg_imagery_index_stereo_cc20', 
#                      columns=load_cols,
#                      where='cloudcover <= {}'.format(cc))
## Mono
fps = query_footprint('dg_imagery_index_all_cc20', 
#                      columns=[load_cols],
                      where='cloudcover <= {}'.format(cc))

stereo_ids = query_footprint('dg_stereo_catalogids', table=True)

## Select only ids not in stereo ids list
fps = fps[~fps['catalogid'].isin(stereo_ids)]

fps['acqdate'] = pd.to_datetime(fps['acqdate'])


#### Start with most recent and work backwards covering AOI
## Find intersection with points
#print('Finding initial intersection with grid...')
if fps.crs != grid.crs:
    grid = grid.to_crs(fps.crs)
#fps_sel = gpd.sjoin(fps, grid, how='inner')
#fps_sel.sort_values(by='acqdate', inplace=True)
#for col in ['index_right', 'index_left']:
#    if col in list(fps_sel):
#        fps_sel.drop(columns=[col], inplace=True)

## Create col to track coverage
grid['covered'] = 0
grid.index = grid.index.set_names(['objID'])
grid.reset_index(inplace=True)


print('Finding secondary intersection with grid...')
# Returns every footprint and point intersection (multiple points and fps)
test = gpd.sjoin(fps, grid, how='left')
# Sort by date for keeping first
test.sort_values(by=['acqdate'], ascending=False, inplace=True)
# Drop duplicate points, keeping first acqdate
test.drop_duplicates(subset=['objID'], keep='first', inplace=True)
test.drop_duplicates(subset=['catalogid'], keep='first', inplace=True)

# Reduce to greater than 
for y in range(2007, 2020):
    perc_covered = None
    subset = test[test['acqdate']>str(y)]
    
    perc_covered = np.where(grid['objID'].isin(subset['objID']), 1, 0)
    covered = len(perc_covered[perc_covered==1])
    total = len(grid)
    perc = ( covered / total ) * 100
    print('{}: '.format(y), len(subset), '{:.2f}%'.format(perc))

#test = test[test.acqdate > '{}'.format(date_min)]

# Write to file
test['acqdate'] = test['acqdate'].apply(lambda x: x.strftime('%Y-%m-%d'))
test.to_file(r'E:\disbr007\imagery_orders\nga_special_use_airspace\stereo_cc{}_post{}.shp'.format(cc, date_min))

## Find missing grid points
#grid['covered'] = np.where(grid['objID'].isin(test['objID']), 1, 0)


#fig, ax = plt.subplots(1,1)
##fps.plot(color='', edgecolor='g', ax=ax)
##fps_sel.plot(color='', edgecolor='b', ax=ax)
#grid.plot(column='covered', ax=ax)
#test.plot(color='black', ax=ax)

#
