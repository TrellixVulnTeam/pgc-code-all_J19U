# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 16:34:57 2019

@author: disbr007
"""

import geopandas as gpd
from id_parse_utils import read_ids

ona = read_ids(r'C:\temp\max_ona_ids.txt')

selection = gpd.read_file(r'C:\Users\disbr007\projects\coastline\coastline.gdb', driver='OpenFileGDB', layer='dg_global_coastline_candidates')

selection = selection[~selection['catalogid'].isin(ona)]

selection.to_file(r'C:\Users\disbr007\projects\coastline\dg_global_coastline_candidates.shp', driver='ESRI Shapefile')
