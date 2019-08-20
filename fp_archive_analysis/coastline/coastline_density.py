# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 11:35:28 2019

@author: disbr007
"""

import arcpy
import geopandas as gpd
import logging
import os
import sys

sys.path.insert(0, r"C:\code\pgc-code-all\fp_archive_analysis")
from archive_analysis_utils import get_count

def update_density_grid(src_grid, coastline, output_grid, distance=0):
    '''
    Takes an empty, global grid and selects only those 
    cells that intersect the coastline at the given distance
    src_grid:  grid polygon, layer or path
    coastline: coastline line, layer or path
    distance: select within distance, in kilometers
    output_grid: write location for updated grid
    '''
    logging.info('''Updating source grid by selecting only those cells within 
                 {} km of coastline.'''.format(distance))
    # Select cells from source grid that intersect within distance of coastline
    updated_grid = arcpy.SelectLayerByLocation_management(src_grid, 
                                                   overlap_type='INTERSECT',
                                                   select_features=coastline,
                                                   search_distance='{} Kilometers'.format(distance),
                                                   selection_type='NEW_SELECTION')
    # Write new grid to file
    output_grid = arcpy.CopyFeatures_management(updated_grid, output_grid)
    


#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


#### arcpy environmental variables
arcpy.env.workspace = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
arcpy.env.overwriteOutput = True


#### Set up paths
## Source data paths
src = 'mfp'
search_distance = 10 # in km
ice_threshold = 20
wd = r'C:\Users\disbr007\projects\coastline'
gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
coast_n = 'GSHHS_f_L1_GIMPgl_ADDant_USGSgl_pline'
candidates_n = '{}_global_coastline_candidates_seaice'.format(src)
grid_n = 'density_grid_one_deg_16x16'


## Output paths
updated_grid_n = '{}_{}km'.format(grid_n, search_distance)
density_n = '{}_global_density_16x16'.format(src)


#### Get Density
## Load feature classes as geodataframes
#update_density_grid(grid_n, coast_n, updated_grid_n, distance=search_distance)

logger.info('Loading candidate footprints: {}'.format(candidates_n))
grid = gpd.read_file(gdb, driver='OpenFileGDB', layer=updated_grid_n)
candidates = gpd.read_file(gdb, driver='OpenFileGDB', layer=candidates_n)

logger.info('Selecting sea-ice concentration <= {}'.format(ice_threshold))
candidates = candidates[candidates['sea_ice_co'] <= ice_threshold]

## Count candidates per grid cell, any intersecting footprint
## is counted. Footprints can be counted more than once.
logger.info('Getting count of candidates per cell.')
density = get_count(grid, candidates)
density.to_file(os.path.join(wd, '{}.shp'.format(density_n)), driver='ESRI Shapefile')

logger.info('Done.')

