# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 09:14:08 2020

@author: disbr007
"""

import logging.config
import matplotlib.pyplot as plt
import numpy as np

import cv2
from osgeo import gdal

from misc_utils.RasterWrapper import Raster
from misc_utils.raster_clip import warp_rasters
from misc_utils.logging_utils import LOGGING_CONFIG


#### INPUTS ####
# tandemx_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\pc_align\tandemx\dem\tdm90_banks_3413_aoi6_clip_resample_pca-DEM.tif'
tandemx_path = r'V:\pgc\data\scratch\jeff\ms\scratch\tdm90_banks_3413_aoi6_clip_resample_pca-DEM_clip.tif'
# dem_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\raw\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip.tif'
dem_path = r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip_clip.tif'
# Threshold difference:
# THe size of difference to start eroding at.
diff_thresh = 25

#### SETUP ####
gdal.UseExceptions()
handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)



#### LOAD INPUT DATA ####
tdx = Raster(tandemx_path)
dem = Raster(dem_path)
dem_nodata = dem.nodata_val

tdx_a = tdx.MaskedArray
dem_a = dem.MaskedArray


# Get absolute value differences
abs_diffs = abs(tdx_a - dem_a)

# Set all pixels greater than difference threshold to 1, so that eroding starts from them
seeded_diffs = np.ma.where(abs_diffs > diff_thresh, 1, 0).astype(np.uint8)
kernel = np.ones((5,5), np.uint8)
# Do the erosion
eroded = cv2.dilate(seeded_diffs, kernel, iterations = 2)
# Mask originally masked pixels
eroded = np.ma.masked_where(np.ma.getmask(dem_a), eroded)
# Take all pixels that are 1's in eroded (pixels larger than diff_thresh and eroded areas) 
# and make NoData in original DEM array
dem_eroded = np.where(eroded == 1, dem_nodata, dem_a)

dem.WriteArray(dem_eroded, r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip_clip_eroded.tif')




#### PLOTTING ####
minx = 500
maxx = 1000
miny = 1250
maxy = 1500

plt.style.use('ggplot')
fig, axes = plt.subplots(1,3,figsize=(18, 7))
# axes[0].imshow(abs_diffs[minx:maxx, miny:maxy])
axes[0].imshow(abs_diffs)
axes[0].set_title('abs_diff')
# axes[1].imshow(seeded_diffs[minx:maxx, miny:maxy])
axes[1].imshow(seeded_diffs)
axes[1].set_title('seeded_diffs')
# axes[2].imshow(eroded[minx:maxx, miny:maxy])
axes[2].imshow(eroded)
axes[2].set_title('eroded')
plt.tight_layout()



# tdx_diff = Raster(tdx_abs_diff_path)
# tdx_diff_a = tdx_diff.MaskedArray
# plt.imshow(tdx_diff_a)