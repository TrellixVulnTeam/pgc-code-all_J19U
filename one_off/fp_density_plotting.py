# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 15:52:49 2019

@author: disbr007
"""

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator

density_path = r'E:\disbr007\imagery_archive_analysis\density\median_alg\density.shp'
driver = 'ESRI Shapefile'
density = gpd.read_file(density_path, driver=driver)

mpl.style.use('ggplot')
fig, ax = plt.subplots(1, 1)
density.hist(column='count', ax=ax)
ax.set(title='Stereo Onhand Over Points')
ax.set(ylabel='Points', xlabel='Stereo Pairs')