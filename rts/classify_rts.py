# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt

import pandas as pd
# from pandas.api.types import is_numeric_dtype
import geopandas as gpd
from shapely.geometry import Polygon

from misc_utils.logging_utils import create_logger
# from obia_utils.neighbors import subset_df, adj_neighbor
from obia_utils.ImageObjects import ImageObjects
from obia_utils.object_plotting import plot_objects

pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'DEBUG')

plt.style.use('pycharm')

ms_img = r'E:\disbr007\umn\2020sep27_eureka\img' \
         r'\ortho_WV02_20140703_test_aoi' \
         r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-' \
         r'M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi.tif'
ndvi = r'E:\disbr007\umn\2020sep27_eureka\img\ndvi_WV02_20140703' \
       r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-500287602150_01_P009_u16mr3413_ndvi.tif'

obj_path = r'E:\disbr007\umn\2020sep27_eureka\scratch\sample_rs_objs_zs.shp'

o = ImageObjects(obj_path)

# Plot objects
# img_kwargs = {'cmap': 'RdYlGn', 'vmin': -0.25, 'vmax': 0.25}
img_kwargs = {}
img = None
linewidth = 1
rgb = [7, 5, 4]
# rgb = None
# band = 1
band = None
# plot_window = (-716225, -825030, -715700, -824534)
plot_window = None
obj_extent = True
column = 'EdgeDens_3'
obj_cmap = None
alpha = 0.9
bounds_only = False
fig, ax = plot_objects(obj=o.objects, img=img, band=band,
                       column=column, obj_cmap=obj_cmap,
                       alpha=alpha, bounds_only=bounds_only,
                       linewidth=linewidth, rgb=rgb,
                       obj_extent=obj_extent, plot_window=plot_window,
                       img_kwargs=img_kwargs)


# Find neighbors
o.get_neighbors(subset=None)
# o.compute_neighbor_values()

# Find headwalls
plt.style.use('pycharm_blank')
fig, ax = plt.subplots(1, 1)

# fields
med = 'MED_mean'
slope = 'slope_mean'
ed = 'EdgeDens_3'
curv = 'curv_pro_3'

hw = o.objects[o.objects[slope] > 5]
hw = hw[hw[ed] > 0.9]
hw = hw[(hw[curv] > -50) & (hw[curv] < 50)]
hw = hw[(hw[med] > -0.5) & (hw[med] < 0.5)]
o.objects.plot(edgecolor='white', color='grey', ax=ax)
hw.plot(edgecolor='red', color='none', ax=ax)
fig.show()
