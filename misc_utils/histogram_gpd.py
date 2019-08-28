# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 11:49:59 2019

@author: disbr007
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

density_p = r'E:\disbr007\imagery_archive_analysis\density\d_itcc20_sixt_ctrs.shp'

density = gpd.read_file(density_p, driver='ESRI Shapefile')

mpl.style.use('ggplot')

density.hist(column=['count'], bins=50)