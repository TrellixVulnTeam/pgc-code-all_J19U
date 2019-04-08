# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 13:06:57 2019

@author: disbr007
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter 
#from osgeo import gdal
import rasterio.plot
import sys, os

def millions(x, pos):
    'The two args are the value and tick position'
    return '%1.1fM' % (x*1e-6)

formatter = FuncFormatter(millions)

dem_path = r'C:\Users\disbr007\umn\ms_proj\data\take3\dems\diff\diff.tif'

with rasterio.open(dem_path) as src:
    dem = src.read(1, masked=True)

dem_cleaned = dem*np.logical_and(dem < 10, dem > -10)

fig, ax = plt.subplots()
rasterio.plot.show_hist(dem_cleaned, bins=np.arange(-5, 5, 0.05), ax=ax)

ax.set_xlabel('Difference: 2017-2010')
ax.set_ylabel('Frequency (Pixels)')
ax.set_title('DEM of Difference')
ax.legend().set_visible(False)
ax.yaxis.set_major_formatter(formatter)


#plt.hist(dem_cleaned, bins=10)