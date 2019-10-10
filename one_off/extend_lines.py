# -*- coding: utf-8 -*-
"""
Created on Fri Sep 27 15:30:04 2019

@author: disbr007
"""

import matplotlib.pyplot as plt
from shapely import geometry
import geopandas as gpd


center_pt = (-77.52685, 167.16537)
endA =  (-77.50778, 167.07707) 
endB = (-77.54592, 167.25366)

mult = 14
    
## Y distances
ya_dist = center_pt[0] - endA[0]
yb_dist = center_pt[0] - endB[0]

## X distances
xa_dist = center_pt[1] - endA[1]
xb_dist = center_pt[1] - endB[1]

## 1km dist
x_1km = xa_dist / 6
y_1km = ya_dist/ 6

## mult dist
twelve_kmA = (center_pt[0]+(y_1km*mult), center_pt[1]+(x_1km*mult))
twelve_kmB = (center_pt[0]-(y_1km*mult), center_pt[1]-(x_1km*mult))

x_diff = 0.5
y_diff = 0.075

sqC = twelve_kmA[0]+y_diff, twelve_kmA[1]+x_diff
sqD = twelve_kmB[0]+y_diff, twelve_kmB[1]+x_diff
pts = [center_pt, endA, endB, twelve_kmA, twelve_kmB, sqC, sqD]
fig, ax = plt.subplots(1,1)
ax.scatter(*zip(*pts))
points = [twelve_kmB, twelve_kmA, sqC, sqD]
print(points)
poly = geometry.Polygon([[p[0], p[1]] for p in points])

gdf = gpd.GeoDataFrame(geometry=[poly], crs={'init':'epsg:4326'})
gdf.plot(ax=ax)
gdf.to_file(r'E:\disbr007\UserServicesRequests\Projects\ksims\erebus_clip2.shp')