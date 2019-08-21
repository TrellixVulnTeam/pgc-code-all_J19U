# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 15:02:22 2019

@author: disbr007
"""


import arcpy
import geopandas as gpd
import logging
import os
import sys

from archive_analysis_utils import get_count
from query_danco import query_footprint, list_danco_footprint

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
grid_gdb = r'E:\disbr007\general\geocell\geocell.gdb'
grid_n = 'one_deg_16x16_arctic'
footprint_n = 'dg_imagery_index_stereo_onhand_cc20'

prj_path = r'C:\Users\disbr007\projects\arctic_intrack_density'
out_gpkg = r'density_arctic'
out_n = r'density_arctic_intrackcc20_onhand'

#grid = gpd.read_file(grid_gdb, layer=grid_n, driver='OpenFileGDB')
#footprint = query_footprint(footprint_n)

logger.info('Calculating density...')
#arctic_density = get_count(grid, footprint)
logger.info('Writing result to GeoJSON...')
geojson_p = os.path.join(prj_path, 'grid.geojson')
#grid.to_file(geojson_p, driver="GeoJSON")
#out_n = 'grid_geojson'
logger.info('Writing GeoJSON to feature class...')
arcpy.env.workspace = grid_gdb
arcpy.JSONToFeatures_conversion(geojson_p, out_n)
