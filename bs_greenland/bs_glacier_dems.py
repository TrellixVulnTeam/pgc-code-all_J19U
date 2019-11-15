# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 15:15:31 2019

@author: disbr007
"""
import os
import matplotlib.pyplot as plt

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from archive_analysis_utils import get_count
from query_danco import query_footprint, list_danco_db


def point_geom(row):
    """
    Create shapely point geometry
    given y and x columns of pandas
    dataframe.
    """
    pt = Point(row['x'], row['y'])
    
    return pt


glacier_pts_p = r'E:\disbr007\projects\boise_greenland_dems\Boxes_CenterCoords.csv'
prj_dir = os.path.dirname(glacier_pts_p)
g_pts = pd.read_csv(glacier_pts_p)
g_pts['geometry'] = g_pts.apply(lambda r: point_geom(r), axis=1)
g_pts = gpd.GeoDataFrame(g_pts, geometry='geometry', crs={'init':'epsg:3413'})

dems = query_footprint('pgc_dem_setsm_strips', where="""cent_lat > 55""")
dems = dems.to_crs({'init':'epsg:3413'})

# Density over each glacier point
dem_density = get_count(g_pts, dems)
#dem_density.to_file(os.path.join(prj_dir, 'glaciers_points_density.shp'))

# Density over greenland geocells
greenland_geocells_p = r'E:\disbr007\general\geocell\geocells_thirty_six_greenland.shp'
greenland_geocells = gpd.read_file(greenland_geocells_p)
greenland_geocells = greenland_geocells.to_crs({'init':'epsg:3413'})
dem_density_geocells = get_count(greenland_geocells, dems)
#dem_density_geocells.to_file(os.path.join(prj_dir, 'greenland_geocell_density.shp'))

# Selection of intersecting DEM footprints
sel = gpd.sjoin(dems, g_pts)
sel.drop_duplicates(subset=['dem_id'], keep='first', inplace=True)
sel.to_file(os.path.join(prj_dir, 'glacier_dem_selection.shp'))

#### Plotting
countries_p = r'E:\disbr007\general\Countries_WGS84\greenland3413.shp'
countries = gpd.read_file(countries_p)
countries = countries.to_crs({'init':'epsg:3413'})

plt.style.use('ggplot')
fig, ax = plt.subplots(1,1)
countries.plot(color='gray', edgecolor='black', ax=ax)
#g_pts.plot(markersize=2, color='r', ax=ax)
dem_density.plot(column='count', ax=ax, legend=True)

fig_h, ax_h = plt.subplots(1,1)
dem_density.hist(column='count', bins=15, ax=ax_h, edgecolor='white')
ax_h.set_title('Glacier DEM Counts')
ax_h.set_xlabel('Number of DEMs')
ax_h.set_ylabel('Glacier Points')
#fig_h.suptitle('Glacier DEM Counts')