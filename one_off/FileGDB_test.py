# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 16:54:06 2019

@author: disbr007
"""

import geopandas as gpd
from osgeo import ogr


gdb = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
read = gpd.read_file(gdb, layer='density_grid_10km', driver='FileGDB')

fgdb = ogr.GetDriverByName('FileGDB')
write = read.to_file(gdb, driver=fgdb, layer='please')
write = read.to_file(gdb, driver='FileGDB', layer='please')