# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 09:14:08 2020

@author: disbr007
"""

import matplotlib.pyplot as plt

from misc_utils.RasterWrapper import Raster


#### INPUTS ####
tandemx_path = r'V:\pgc\data\scratch\jeff\elev\tandemx\tdm90_banks_3413.tif'
dem_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\pc_align\dems\WV02_20130711_1030010025A66E00_1030010025073200_seg1_2m_dem_clip_pca-DEM.tif'


tandemx = Raster(tandemx_path)
dem = Raster(dem_path)
dem_arr = dem.Array

tandemx_ovlp = tandemx.ArrayWindow(dem.get_projwin())
