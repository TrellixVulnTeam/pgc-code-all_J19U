# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 09:14:08 2020

@author: disbr007
"""

import matplotlib.pyplot as plt
import logging.config

import cv2

from misc_utils.RasterWrapper import Raster
from misc_utils.raster_clip import warp_rasters
from misc_utils.logging_utils import LOGGING_CONFIG


#### INPUTS ####
# tandemx_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\pc_align\tandemx\dem\tdm90_banks_3413_aoi6_clip_resample_pca-DEM.tif'
tandemx_path = r'V:\pgc\data\scratch\jeff\ms\scratch\tdm90_banks_3413_aoi6_clip_resample_pca-DEM_clip.tif'
# dem_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\raw\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip.tif'
dem_path = r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip_clip.tif'

#### SETUP ####
handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)



#### LOAD INPUT DATA ####
tdx = Raster(tandemx_path)
dem = Raster(dem_path)

tdx_a = tdx.MaskedArray
dem_a = dem.MaskedArray


# Get absolute value differences
abs_diffs = abs(tdx_a - dem_a)
del tdx_a, dem_a, tdx, dem









# plt.imshow(tdx_a)
# plt.title('Tandem-X')



# tdx_diff = Raster(tdx_abs_diff_path)
# tdx_diff_a = tdx_diff.MaskedArray
# plt.imshow(tdx_diff_a)