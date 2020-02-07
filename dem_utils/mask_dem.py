# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 09:14:08 2020

@author: disbr007
"""

import matplotlib.pyplot as plt

from misc_utils.RasterWrapper import Raster
from misc_utils.raster_clip import warp_rasters


#### INPUTS ####
tandemx_path = r'V:\pgc\data\scratch\jeff\elev\tandemx\tdm90_banks_3413.tif'
dem_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\pc_align\dems\WV02_20130711_1030010025A66E00_1030010025073200_seg1_2m_dem_clip_pca-DEM.tif'
aoi_path = r'E:\disbr007\umn\ms\shapefile\aois\pot_aois\aoi6_2020feb01.shp'
# Directory for clipped TanDEMX
tandemx_clipped_dir = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems'


#### SETUP ####
# List of files to clean-up
remove_files = []

#### CLIP TANDEMX AOI ####
tandemx_aoi = warp_rasters(aoi_path, [tandemx_path],
                           out_dir=tandemx_clipped_dir,
                           out_suffix='_aoi6_clip')[0]
remove_files.append(tandemx_aoi)

