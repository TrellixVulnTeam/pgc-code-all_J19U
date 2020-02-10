# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 09:14:08 2020

@author: disbr007
"""

import logging.config
import matplotlib as mpl
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
# This number is not the exact elevation difference that will be excluded -> convolution
diff_thresh = 40

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


#### Convolve absolute differences to include areas around them ####
# Convolve absolute differences to include areas around them
# Kernel setup
kernel_size = 9
kernel = np.ones((kernel_size,kernel_size), dtype=np.float32) * 2
width, height = kernel.shape
center_width = int((width - 1)/2)
center_height = int((height - 1)/2)
kernel[center_width, center_height] = 9
kernel = kernel / 9

convolved = cv2.filter2D(abs_diffs, -1, kernel=kernel,
                         borderType=cv2.BORDER_CONSTANT)

cleaned = np.ma.where(convolved >= diff_thresh, dem_nodata, dem_a)
cleaned = np.ma.masked_where(cleaned == dem_nodata, cleaned)
dem.WriteArray(cleaned, r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip_clip_conv{}_{}.tif'.format(kernel_size, diff_thresh))




#### PLOTTING ####
minx = 500
maxx = 1000
miny = 1250
maxy = 1500

plt.style.use('ggplot')

# colorbar
cmap = plt.cm.jet  # define the colormap
# extract all colors from the .jet map
cmaplist = [cmap(i) for i in range(cmap.N)]
# force the first color entry to be grey
cmaplist[0] = (.5, .5, .5, 1.0)

# create the new map
cmap = mpl.colors.LinearSegmentedColormap.from_list(
    'Custom cmap', cmaplist, cmap.N)

# define the bins and normalize
bounds = np.linspace(dem_a.min(), dem_a.max())
norm = mpl.colors.BoundaryNorm(bounds, cmap.N)


fig, axes = plt.subplots(1,3,figsize=(18, 7))
# axes[0].imshow(abs_diffs[minx:maxx, miny:maxy])
axes[0].imshow(abs_diffs, cmap=cmap, norm=norm)
axes[0].set_title('abs_diff')
# axes[1].imshow(seeded_diffs[minx:maxx, miny:maxy])
axes[1].imshow(convolved, cmap=cmap, norm=norm)
axes[1].set_title('covolved')
axes[2].imshow(cleaned, cmap=cmap, norm=norm)
axes[2].set_title('cleaned')
plt.tight_layout()



# tdx_diff = Raster(tdx_abs_diff_path)
# tdx_diff_a = tdx_diff.MaskedArray
# plt.imshow(tdx_diff_a)



# # Set all pixels greater than difference threshold to 1, so that eroding starts from them
# seeded_diffs = np.ma.where(abs_diffs > diff_thresh, 1, 0).astype(np.uint8)
# kernel = np.ones((5,5), np.uint8)
# # Do the erosion
# eroded = cv2.dilate(seeded_diffs, kernel, iterations = 2)
# # Mask originally masked pixels
# eroded = np.ma.masked_where(np.ma.getmask(dem_a), eroded)
# # Take all pixels that are 1's in eroded (pixels larger than diff_thresh and eroded areas) 
# # and make NoData in original DEM array
# dem_eroded = np.where(eroded == 1, dem_nodata, dem_a)
