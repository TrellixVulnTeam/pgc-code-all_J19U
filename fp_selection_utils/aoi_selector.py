# -*- coding: utf-8 -*-
"""
Created on Mon Jan 28 13:11:20 2019

@author: disbr007
Select imagery to cover an AOI completely while minimizing overlap/redundacy
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, shape, mapping
import fiona
import numpy as np
import os

def create_index_grid(input_shp_path, step):
    '''must be rectangular'''
    aoi = gpd.read_file(input_shp_path)
    aoi_crs = aoi.crs
    
    xmin, ymin, xmax, ymax = aoi.total_bounds # bounding box for input_shp
    
    bottom_left = xmin, ymin # bottom left corner - starting point
    top_right = xmax, ymax # top right corner - ending point
    
    step = step # grid cell size in units of projection (?)
    
    grid_cells =[] # store each cell until writing to geodataframe
    x = bottom_left[0] # start at bottom left
    while x < top_right[0]: # until hitting right side
        y = bottom_left[1] # start with bottom row
        while y < top_right[1]: # until hitting top
            cell = Polygon([(x,y), (x, y+step), (x+step, y+step), (x+step, y)]) # bounds of grid cell, counter clockwise from lower left
            grid_cells.append(cell)
            y += step # move up one row
        x += step # move right one column
    grid = gpd.GeoDataFrame({'geometry': grid_cells})
    grid['covered'] = 0
    grid['id'] = grid.index
    grid.crs = aoi_crs 
    grid_out_path = os.path.join(project_path, 'aoi_grid.shp')
#    grid.to_file(grid_out_path)
    
    return grid

def select_overlap(index_grid, footprint_path):
    '''identifies overlapping features in index grid and footprints. changes values in index to 1'''
    footprint = gpd.read_file(footprint_path)
    overlap = gpd.sjoin(index_grid, footprint, how='inner')
    overlap['covered'] = 1
    overlap.pop('index_right')
    overlap.pop('Name')
    overlap.crs = index_grid.crs
    updated_grid = pd.concat([overlap, index_grid])
    updated_grid.drop_duplicates(subset='id', keep='first', inplace=True)
    return updated_grid


project_path = r"C:\Users\disbr007\scripts\aoi_selector\test_data"
aoi_path = os.path.join(project_path, "aoi.shp")
footprint_path = os.path.join(project_path, "imagery_footprints.shp")

idx_grid = create_index_grid(aoi_path, step=0.005)
idx_grid2 = select_overlap(idx_grid, footprint_path)
idx_grid2.to_file(os.path.join(project_path, 'overlapping.shp'), driver='ESRI Shapefile')

#def calc_overlap(footprint)
#fp_shp = fiona.open(footprint_path)

# Loop over footprints in footprint shapefile, calculate overlap with AOI, write to new shapefile.
with fiona.open(footprint_path, 'r') as fp_shp:
    idx_shp = fiona.open(aoi_path)
    
    idx_geom = [ shape(feat['geometry']) for feat in idx_shp ]
    fp_geom = [ shape(feat['geometry']) for feat in fp_shp ]
    
    schema = fp_shp.schema.copy()
    fp_shp_crs = fp_shp.crs
    
    schema['properties']['perc_ovlp'] = 'float'
    out_shp_path = os.path.join(project_path, 'aoi_perc_ovlp.shp')
    
    with fiona.open(out_shp_path, 'w', 'ESRI Shapefile', schema, fp_shp_crs) as output:
        for idx_feat in idx_shp:
            idx_geom = shape(idx_feat['geometry'])
            for fp_feat in fp_shp:
                fp_geom = shape(fp_feat['geometry'])
                if idx_geom.intersects(fp_geom):
                    area_ovlp = round((idx_geom.intersection(fp_geom).area / idx_geom.area) * 100)
                    fp_feat['properties']['perc_ovlp'] = area_ovlp
                    output.write({'properties':fp_feat['properties'],'geometry':mapping(shape(fp_feat['geometry']))})

#for i in idx_geom:
#    for f in fp_geom: 
#        if i.intersects(f):
#            area_overlap = (i.intersection(f).area / i.area) * 100
#            feat['properties']['perc_ovlp'] = area_overlap
#            print(area_overlap)


#        print(fp_feat)



