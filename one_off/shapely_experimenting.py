# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 09:35:56 2019

@author: disbr007
"""

from shapely.geometry import Point, LineString, Polygon
from shapely.ops import nearest_points
import matplotlib.pyplot as plt
import geopandas as gpd
from scipy.spatial import cKDTree

import pandas as pd


poly_pts = [Point((1.0,2.0)), Point((1.0, 1.0)), Point((2.0, 1.0)), Point((2.0, 2.0))]
pts = [Point((0.0,2.0)), Point((0.0, 1.0))]
poly = Polygon([[p.x, p.y] for p in poly_pts])
line = LineString([Point(0,0),Point(2,0)])

np = list(nearest_points(poly, line))

poly_gdf = gpd.GeoDataFrame(geometry=[poly])
pts_gdf = gpd.GeoDataFrame(geometry=pts)
line_gdf = gpd.GeoDataFrame(geometry=[line])
np_gdf = gpd.GeoDataFrame(geometry=np)

fig, ax = plt.subplots()
line_gdf.plot(ax=ax)
pts_gdf.plot(ax=ax)
poly_gdf.plot(ax=ax, edgecolor='red', color='')
np_gdf.plot(ax=ax, markersize=12, color='purple')

distance = np[0].distance(np[1])

