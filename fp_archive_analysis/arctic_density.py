# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 14:50:25 2019

@author: disbr007
Arctic Stereo Density
"""

import geopandas as gpd
import matplotlib.pyplot as plt

from archive_analysis_utils import get_density


## Load Arctic Geocells
driver = 'ESRI Shapefile'
geocells_path = r'E:\disbr007\general\geocell\Global_GeoCell_Coverage.shp'
#geocells_path = r'E:\disbr007\scratch\geocells_sub.shp' # testing subset of 15 geocells
arc_cells = gpd.read_file(geocells_path, driver=driver)
arc_cells = arc_cells[arc_cells.region == 'arctic']

arc_density = get_density('dg_imagery_index_stereo', arc_cells)

arc_density.to_file(r'E:\disbr007\scratch\density_debug\arc_density.shp', driver=driver)