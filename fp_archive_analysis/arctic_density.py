# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 14:50:25 2019

@author: disbr007
Arctic Stereo Density
"""

import geopandas as gpd
import matplotlib.pyplot as plt

from archive_analysis_utils import get_density, grid_aoi


## Load Arctic Geocells
driver = 'ESRI Shapefile'
geocells_path = r'E:\disbr007\scratch\geocells_sub_single.shp'
#geocells_path = r'E:\disbr007\scratch\geocells_sub.shp' # testing subset of 15 geocells
arc_cells = gpd.read_file(geocells_path, driver=driver)
arc_cells = arc_cells[arc_cells.region == 'arctic']

# Subset geocells into grid of four points 
arc_cell_grid = grid_aoi(geocells_path, step=2)
#arc_density = get_density('dg_imagery_index_stereo', arc_cells)

#arc_density.to_file(r'E:\disbr007\scratch\density_debug\arc_density.shp', driver=driver)

## Plot for testing
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
# Plot data
ax = world[world.continent == 'North America'].plot(
    color='white', edgecolor='black')
arc_cells.plot(ax=ax, color='', edgecolor='red')
arc_cell_grid.plot(ax=ax, color='red')

# Adjust figure
minx, miny, maxx, maxy = arc_cells.total_bounds
xstep = (maxx - minx) / 10
ystep = (maxy- miny) / 10
ax.set_xlim(minx-xstep, maxx+xstep)
ax.set_ylim(miny-ystep, maxy+ystep)
plt.show()
