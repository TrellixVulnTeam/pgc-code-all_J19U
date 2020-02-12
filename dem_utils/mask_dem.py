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
tandemx_path = r'V:\pgc\data\scratch\jeff\ms\scratch\tdm90_banks_3413_aoi6_clip_resamp_bil_pca-DEMmask_test.tif'
dem_path = r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_1030010036966A00_1030010036846B00_seg1_2m_dem_clip_clip.tif'
# Threshold difference:
# This number is not the exact elevation difference that will be excluded,
# it is the value that will be removed after convolution.
# conv_diff_thresh = 40
# Raw minimum difference in DEMs to count as error/blunder, this is 
# used when creating the 'missed_errors' raster and plot
# error_thresh = 12


def clean_dem(dem, abs_diffs,
              conv_diff_thresh, error_thresh,
              dem_nodata,
              kernel_base=None, kernel_center=None, 
              kernel_size=3, kernel=None,
              ):
    """
    Removes errors from a dem by convolving a kernel over the differences of the DEM
    to erode smaller differences adjacent to large differences.

    Parameters
    ----------
    dem : np.array
        The array to 'clean'
    abs_diffs : np.array
        An array of absolute values of errors (e.g. from differencing with another DEM)
    kernel_base : INT or FLOAT
        The value to use in the kernel, except for center.
    kernel_center : INT or FLOAT
        The value to use in the center of the kernel.
    conv_diff_thresh : INT or FLOAT
        The threshold of errors to remove after convolution.
    error_thresh : INT or FLOAT
        The size of differences to consider errors when evaluating results.
    kernel_size : INT, optional
        The size of the height and width of the kernel. The default is 3.
    kernel : np.array, optional
        ALternatively, can specify the kernel to use. The default is None.
    
    Returns
    -------
    results : dict
        A dictionary containing the cleaned DEM, an array with 1's for omitted errors,
        the number of omitted errors, and the number of included erros.

    """
# ###
# #### LOAD INPUT DATA ####
# tdx = Raster(tandemx_path)
# dem = Raster(dem_path)
# dem_nodata = dem.nodata_val

# tdx_a = tdx.MaskedArray
# dem_a = dem.MaskedArray
# # # Get absolute value differences
# abs_diffs = abs(tdx_a - dem_a)

# kernel_center = 9
# kernel_base = 2
# kernel=None
# ###
    if not kernel:
        # Convolve absolute differences to include areas around them
        # Kernel setup
        kernel_size = 3
        kernel = np.ones((kernel_size,kernel_size), dtype=np.float32) * kernel_base
        width, height = kernel.shape
        center_width = int((width - 1)/2)
        center_height = int((height - 1)/2)
        kernel[center_width, center_height] = kernel_center
        kernel = kernel / 9
    
    
    # Convolution
    convolved = cv2.filter2D(abs_diffs, -1, kernel=kernel,
                             borderType=cv2.BORDER_CONSTANT)
    
    # Where greater than conv threshold, put NoData, else put the DEMs values
    cleaned = np.ma.where(convolved >= conv_diff_thresh, dem_nodata, dem_a)
    # Mask the DEM where it equals no data
    cleaned = np.ma.masked_where(cleaned == dem_nodata, cleaned)
    np.ma.set_fill_value(cleaned, dem_nodata)
    # dem.WriteArray(cleaned, 
    #                r'V:\pgc\data\scratch\jeff\ms\scratch\WV02_20140902_convks{}kb{}kc{}_{}.tif'.format(kernel_size,
    #                                                                                                    kernel_base,
    #                                                                                                    kernel_center,
    #                                                                                                    conv_diff_thresh))
    
    
    #### MISSED ERRORS ####
    # Get all of the errors over threshold that were not masked as a 1-d array with actual values
    rem_abs_errors = np.ma.where((cleaned.mask == False) & (abs_diffs.data > error_thresh), abs_diffs, 0)
    # Reapply the original mask
    rem_abs_errors = np.ma.masked_where(cleaned.mask == True, rem_abs_errors)
    
    # Count number of 'valid' (diff less than error thresh) pixels that were omitted
    omitted_valid = np.ma.where((abs_diffs < error_thresh) & (cleaned.mask == True), abs_diffs.data, 0)
    num_omitted_valid = omitted_valid[omitted_valid != 0].size
    
    # Count number of 'errors' (diff greater than error thresh) pixels that were kept in DEM
    # included_err = np.ma.where((abs_diffs > error_thresh) & (cleaned != dem.nodata_val), 1, 0)
    inc_err = np.ma.where((abs_diffs.data > error_thresh) & (cleaned.mask == False), abs_diffs.data, 0)
    num_inc_err = inc_err[inc_err!=0].size
    
    # Get all of the errors that were not masked as a 1, 0 array, with omitted valid data as 2
    # omitted valid = 2
    rem_errors_bin = np.ma.where(omitted_valid!=0, 2, 0)
    # kept bad = 1
    rem_errors_bin = np.ma.where((rem_errors_bin != 2) & (abs_diffs.data > error_thresh) & (cleaned.mask == False), 1, rem_errors_bin)
    # good data not excluded = 0
    rem_errors_bin = np.ma.masked_where((rem_errors_bin != 2) * (rem_errors_bin != 1) * (cleaned.mask == True), rem_errors_bin)
    
    
    ## PLOTTING ##
    # colormap for DEMs and difference
    cmap = plt.cm.viridis  # define the colormap
    # extract all colors from the .jet map
    cmaplist = [cmap(i) for i in range(cmap.N)]
    # force the first color entry to be grey
    cmaplist[0] = (.5, .5, .5, 1.0)
    # create the new map
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        'Custom cmap', cmaplist, cmap.N)
    # define the bins and normalize
    bounds = np.linspace(rem_abs_errors.min(), rem_abs_errors.max())
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
    
    fig, ax = plt.subplots(2,2, figsize=(20,10))
    fig.suptitle('cv{} er{} kc{} kb{}'.format(conv_diff_thresh, error_thresh, kernel_center, kernel_base))
    ax = ax.flatten()
    ax[0].imshow(rem_errors_bin)
    ax[0].set_title('rem errors bin')
    ax[1].imshow(rem_abs_errors, cmap=cmap, norm=norm)
    ax[1].set_title('rem abs errors')
    ax[2].imshow(abs_diffs)
    ax[2].set_title('abs_diffs')
    ax[3].imshow(dem)
    ax[3].imshow('dem')
    plt.tight_layout()
        

    logger.info('Kernel Center: {}'.format(kernel_center))
    logger.info('Kernel Base: {}'.format(kernel_base))
    logger.info('Missed errs mean: {:.2f}'.format(rem_abs_errors.mean()))
    logger.info('Missed errs std : {:.2f}'.format(rem_abs_errors.std()))
    logger.info('Missed errs max: {:.2f}'.format(rem_abs_errors.max()))
    logger.info('Missed errs min: {:.2f}'.format(rem_abs_errors.min()))
    logger.info('Missed errs ci95: {:.2f}-{:.2f}\n'.format(rem_abs_errors.mean() - rem_abs_errors.std()*1.96,
                                                  rem_abs_errors.mean() + rem_abs_errors.std()*1.96))
    
    
    
    
    results = {'cleaned': cleaned,
                'rem_errors_bin': rem_errors_bin,
                'omitted_valid': num_omitted_valid,
                'included_err': num_inc_err,
              }
    
    return results


# #### SETUP ####
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
arr_dict = {}
kernel_bases = [2.25]
kernel_centers = [11]
error_threshs = [12]
conv_diff_threshs = [30, 40, 50]

for cdv in conv_diff_threshs:
    for er in error_threshs:
        for kc in kernel_centers:
            for kb in kernel_bases:
                arr_dict['conv{}_err{}_kc{}_kb{}'.format(cdv, er, kc, kb)] = clean_dem(dem=dem_a,
                                                                  abs_diffs=abs_diffs,
                                                                  conv_diff_thresh=cdv,
                                                                  error_thresh=er,
                                                                  dem_nodata=dem.nodata_val,
                                                                  kernel_base=kb, kernel_center=kc)


#### PLOTTING ####
# Plot window if used
minx = 500
maxx = 1000
miny = 1250
maxy = 1500


plt.style.use('ggplot')
# Potting styling
mpl.rcParams['axes.facecolor'] = '#383838'
mpl.rcParams['figure.facecolor'] = '#242424'
mpl.rcParams['text.color'] = 'white'
mpl.rcParams['xtick.color'] = 'white'
mpl.rcParams['ytick.color'] = 'white'

mpl.rcParams['grid.color'] = '#DCDCDC'
mpl.rcParams['grid.linewidth'] = 0.2

# colormap for DEMs and difference
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
# Black and red cmap
bw_cmap = mpl.colors.ListedColormap(['black', 'red'])


# Create figure
# Get closest square
num_plots = len(arr_dict.keys())
squares = [1, 4, 9, 16, 25]
closest_sq = min(squares, key=lambda x:abs(x-num_plots))
subplot_width = int(np.sqrt(closest_sq))

fig, axes = plt.subplots(subplot_width, subplot_width,figsize=(16, 10))
# fig.suptitle('Conv:{}  Error: {}'.format(conv_diff_thresh, error_thresh))

# axes[0].imshow(abs_diffs[minx:maxx, miny:maxy])
if subplot_width > 1:
    axes = axes.flatten()
else:
    axes = [axes]

for i, (k, v) in enumerate(arr_dict.items()):
    axes[i].set_title(k)
    axes[i].imshow(v['rem_errors_bin'])
    axes[i].annotate('Omitted valid: {:,.0f}$m^2$\nIncluded errors: {:,.0f}$m^2$'.format(v['omitted_valid']/4, 
                                                                                  v['included_err']/4),
                      xy=(0.05, 0.80), xycoords='axes fraction')

# axes[0].imshow(abs_diffs, cmap=cmap, norm=norm)
# axes[0].set_title('abs_diff')
# axes[1].imshow(seeded_diffs[minx:maxx, miny:maxy])
# axes[1].imshow(convolved, cmap=cmap, norm=norm)
# axes[1].set_title('covolved')
# axes[2].imshow(cleaned, cmap=cmap, norm=norm)
# axes[2].set_title('cleaned')
# axes[3].imshow(missed_errs_mask, cmap=bw_cmap)
# axes[3].set_title('missed errors')
plt.tight_layout()
