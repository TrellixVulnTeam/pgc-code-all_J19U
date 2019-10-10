# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 14:33:37 2019

@author: disbr007
Converts old filepaths for a DEM selection .shp to Earth DEM region
"""


import geopandas as gpd
import os

from query_danco import query_footprint

#### Paths
## Project path
prj_p = r'E:\disbr007\umn\ms_proj_'

## DEMs selection shapefile
dem_sel_p = os.path.join(prj_p, r'data\shapefile\pgc_dem_setsm_strips_banks_hstks_selection.shp')

#### Load data
earthdem_regions = query_footprint(layer='pgc_earthdem_regions')
dem_sel = gpd.read_file(dem_sel_p)

#### Spatial join DEMs to earthdem regions to identify 
dem_sel = gpd.sjoin(dem_sel, earthdem_regions, how='left')  
dem_sel['region'] = dem_sel.apply(lambda x: x['region_id'], axis=1)

