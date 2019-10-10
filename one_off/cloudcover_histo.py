# -*- coding: utf-8 -*-
"""
Created on Mon Oct  7 16:05:42 2019

@author: disbr007
"""

import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

shp_p = r'E:\disbr007\imagery_orders\change_detection_aois\OY1_Test_Site_AOIs_selection.shp'

shp = gpd.read_file(shp_p, driver='ESRI Shapefile')

shp['acqdate'] = pd.to_datetime(shp['acqdate'])

monthly = shp.set_index('acqdate').groupby(pd.Grouper(freq='M')).agg({'catalogid':'count'})

plt.style.use('ggplot')
shp.hist('cloudcover')
monthly.plot()