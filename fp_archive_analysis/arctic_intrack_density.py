# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 15:02:22 2019

@author: disbr007
"""


import geopandas as gpd
import logging
import os
import sys

from archive_analysis_utils import get_count
from query_danco import query_footprint

#### Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


#### Load grid and footprint
logger.info('Loading grid and footprint...')
gdb = r'C:\Users\disbr007\projects\arctic_intrack_density\arctic_intrack_density.gdb'
prj_path = r'C:\Users\disbr007\projects\arctic_intrack_density'

footprint_n = 'dg_imagery_index_stereo_cc20'

grid_n = 'one_deg_16x16_arctic'
#out_n = r'density_arctic_intrackcc20_onhand'

footprint = query_footprint(footprint_n)

process = [('one_deg_16x16_arctic', 'arctic_density_intrackcc20'),
           ('one_deg_16x16_nam', 'NAm_density_intrackcc20'),
           ('one_deg_geocell', 'global_density_intrackcc20')]

for g, on in process:
    print(g, on)
    grid = gpd.read_file(gdb, layer=g, driver='OpenFileGDB')    
    logger.info('Calculating density...')
    arctic_density = get_count(grid, footprint)
    
    logger.info('Writing density to shapefile {}'.format(on))
    arctic_density.to_file(os.path.join(prj_path, '{}.shp'.format(on)))
    