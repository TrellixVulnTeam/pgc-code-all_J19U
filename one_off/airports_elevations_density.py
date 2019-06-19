# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 16:31:51 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os, argparse, sys
import matplotlib.pyplot as plt

from shapely.geometry import Point
sys.path.insert(0, "c:\code\archive_analysis")
from archive_analysis_utils import get_density



ap_path = r"E:\disbr007\imagery_archive_analysis\density\airport\ak_airports.txt"

with open(ap_path, 'r') as f:
    content = f.readlines()
    
    lat = []
    lon = []
    elv = []
    apc = []
    
    for line in content:
        # seperate by spaces - variable number between elements
        line_lst = line.split(' ')
        # removes empty strings
        line_lst = [x.rstrip("\n\r") for x in line_lst if x != '']
        # Assign each element to appropriate dict col
        lat.append(float(line_lst[0]))
        lon.append(-float(line_lst[1]))
        elv.append(line_lst[2])
        apc.append(' '.join(line_lst[3:]))

# Create dictionary of lists and column names
ap_dict = {'lat': lat, 'lon': lon, 'elv': elv, 'apc': apc}
# Create pandas df
ap = pd.DataFrame.from_dict(ap_dict)
# Create Points
ap['coords'] = [Point(x, y) for x, y in zip(ap.lon, ap.lat)]
# Convert to gpd df
ap = gpd.GeoDataFrame(ap, geometry=ap.coords, crs={'init':'epsg:4326'})
ap.drop(columns=['coords'], inplace=True)


## Plot points
#world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
## We restrict to South America.
#ax = world[world.continent == 'North America'].plot(
#    color='white', edgecolor='black')
#
## We can now plot our GeoDataFrame.
#ap.plot(ax=ax, color='red')
#plt.show()

ap_density = get_density('dg_imagery_index_stereo', ap, write_path=r'E:\disbr007\imagery_archive_analysis\density\airport')
