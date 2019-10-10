# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 21:47:14 2019

@author: disbr007
"""

import arcpy
import logging
import os
import sys

from coastline.coastline_candidates_arcpy import coastline_candidates
from coastline.coastline_sea_ice_arcpy import coastline_sea_ice
from coastline.coastline_density_arcpy import coastline_density
from coastline.coastline_density import gpd_get_density

#### Setup
working_dir = r'C:\Users\disbr007\projects\coastline'
gdb = r'C:\Users\disbr007\projects\coastline\coast.gdb'

arcpy.env.workspace = gdb
arcpy.env.overwriteOutput = True

## Name of coastline feature class in gdb
coastline = r'GSHHS_f_L1_GIMPgl_ADDant_USGSgl_pline'

## Which footprint to find cnadidates from - can be 
srcs = ['mfp'] #'nasa' #'dg'
distance = 10 # search distance in km from coastline

## Sea ice percentage above which to exclude (<=)
ice_threshold = 20

## Update the dictionaries that hold the paths to all 
## sea ice rasters that have been downloaded
update_luts = False

## Name of grid feature class to sample density on
grid = 'density_grid_one_deg_16x16_10km'


#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(os.path.join(working_dir, 'coastline_selection_density2019aug22.log'))
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)


#srcs = ['mfp', 'nasa', 'dg']
#srcs = ['oh']
for src in srcs:
    logging.info('****WORKING ON {}****'.format(src.upper()))
    initial_candidates = '{}_global_coastline_candidates'.format(src)
    final_candidates = '{}_final_candidates'.format(src)
    density_name = '{}_density'.format(src)
    
    
#    if src != 'mfp':
    logger.info('FINDING INITAL CANDIDATES...')
    coastline_candidates(src=src,
                         gdb=gdb,
                         wd=working_dir,
                         coast_n=coastline,
                         distance=10,
                         out_name=initial_candidates)

    logger.info('LOOKING UP SEA ICE AND THRESHOLDING...')
    coastline_sea_ice(src=src,
                      initial_candidates=initial_candidates,
                      final_candidates=final_candidates,
                      gdb=gdb,
                      wd=working_dir,
                      ice_threshold=ice_threshold,
                      update_luts=update_luts)
    
    logger.info('CALCULATING DENSITY...')
    coastline_density(src=src,
                      final_candidates=final_candidates,
                      grid=grid,
                      density_name=density_name)
    gpd_get_density(final_candidates, grid, density_name, gdb=gdb, wd=working_dir)
