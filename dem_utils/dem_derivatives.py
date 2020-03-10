# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 13:52:48 2019

@author: disbr007
DEM Derivatives
"""

## Standard Libs
import argparse
import copy
import logging.config
import os
import sys
import numpy as np

## Third Party Libs
import cv2
from osgeo import gdal
from scipy.ndimage.filters import generic_filter

## Local libs
from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger, LOGGING_CONFIG
from misc_utils.array_utils import interpolate_nodata


gdal.UseExceptions()

handler_level = 'DEBUG'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def gdal_dem_derivative(input_dem, output_path, derivative, return_array=False, **args):
    '''
    Take an input DEM and create a derivative product
    input_dem: DEM
    derivative: one of "hillshade", "slope", "aspect", "color-relief", "TRI", "TPI", "Roughness"
    return_array: optional argument to return the computed derivative as an array. (slow IO as it just loads the new file.)
    Example usage: slope_array = dem_derivative(dem, 'slope', array=True)
    '''

    supported_derivatives = ["hillshade", "slope", "aspect", "color-relief", 
                             "TRI", "TPI", "Roughness"]
    if derivative not in supported_derivatives:
        logging.error('Unsupported derivative type. Must be one of: {}'.format(supported_derivatives))
        sys.exit()

#    out_name = '{}_{}.tif'.format(os.path.basename(input_dem).split('.')[0], derivative)
#    out_path = os.path.join(os.path.dirname(input_dem), out_name)

    # if args:
        # dem_options = gdal.DEMProcessingOptions(args)

    gdal.DEMProcessing(output_path, input_dem, derivative, **args)

    if return_array:
        from RasterWrapper import Raster
        array = Raster(output_path).Array

        return array


def calc_tpi(dem, size):
    """
    OpenCV implemntation of TPI, updated to ignore NaN values.
    
    Parameters
    ----------
    dem : np.ndarray
        Expects a MaskedArray with a fill value of the DEM nodata value
    size : Size of kernel along one axis. Square kernel used.

    Returns
    ----------
    np.ndarray (masked) : TPI
    """
    logger.info('Computing TPI with kernel size {}...'.format(size))
    # Set up 'kernel'
    window = (size, size)
    window_count = size*size

    # Get original mask
    # mask = copy.deepcopy(dem.mask)

    # # Change fill value to -9999 to ensure NaN corrections are applied correctly
    # nodata_val = -9999
    # dem.fill_value = nodata_val
    nodata_val = dem.fill_value

    # Count the number of non-NaN values in the window for each pixel
    logger.debug('Counting number of valid pixels per window...')
    num_valid_window = cv2.boxFilter(np.logical_not(dem.mask).astype(int), -1, window, normalize=False,
                                     borderType=cv2.BORDER_REPLICATE)

    # Change masked values to fill value
    dem = dem.data

    # Get raw sum within window for each pixel
    logger.debug('Getting raw sum including NoData values...')
    sum_window = cv2.boxFilter(dem, -1, window, normalize=False, borderType=cv2.BORDER_REPLICATE)
    
    # Correct these sums by removing (fill value*number of times it was include in the sum) for each pixel
    logger.debug('Correcting for inclusion of NoData values...')
    sum_window = np.where(num_valid_window != window_count, # if not all pixels in window were valid
                          sum_window+(-nodata_val*(window_count-num_valid_window)), # remove NoData val from sum for each time it was included
                          sum_window)

    # Compute TPI (value - mean of value in window)
    logger.debug('Calculating TPI...')
    with np.errstate(divide='ignore',invalid='ignore'):
        tpi = dem - (sum_window/num_valid_window)
    # Remask any originally masked pixels
    tpi = np.ma.masked_where(dem.data==nodata_val, tpi)
    # tpi = np.ma.masked_where(mask, tpi)

    return tpi


# def calc_tpi(dem, size):
    """
    OpenCV implementation of TPI
    dem: array
    size: int, kernel size in x and y directions (square kernel)
    Note - borderType determines handline of edge cases. REPLICATE will take the outermost row and columns and extend
    them as far as is needed for the given kernel size.
    """
    logger.info('Computing TPI with kernel size {}...'.format(size))
    # To attempt to clean up artifacts that I believe are a results of
    # no data values being included in interpolation. So interpolate 
    # closest values to no data instead of no data. values that were no
    # data are masked out again at the end.
    # Interpolate nodata, cubic method leaves no data at edges
    # logger.debug('Interpolating no data values...')
    # dem = interpolate_nodata(dem, method='cubic')
    # Clean up edges with simple nearest interpolation
    logger.debug('Cleaning up edge no data values...')
    dem = interpolate_nodata(dem, method='nearest')

    kernel = np.ones((size,size),np.float32)/(size*size)
    # -1 indicates new output array
    dem_conv = cv2.filter2D(dem, -1, kernel, borderType=cv2.BORDER_REPLICATE)
    tpi = dem - dem_conv
    
    return tpi


def calc_tpi_dev(dem, size):
    """
    Based on (De Reu 2013)
    Calculates the tpi/standard deviation of the kernel to account for surface roughness.
    dem: array
    size: int, kernel size in x and y directions (square kernel)
    """
    tpi = calc_tpi(dem, size)
    
    # Calculate the standard deviation of each cell, mode='nearest' == cv2.BORDER_REPLICATE
    std_array = generic_filter(dem, np.std, size=size, mode='nearest')

    tpi_dev = tpi / std_array

    return tpi_dev


def dem_derivative(dem, derivative, output_path, size, **args):
    """
    Wrapper function for derivative functions above.
    
    Parameters
    ----------
    dem : os.path.abspath
        Path to the source DEM.
    derivative : STR
        Name of the derivative to create. One of:
            tpi_ocv
            gdal_hillsahde, gdal_slope, gdal_aspect,
            gdal_color-relief, gdal_tpi, gdal_tri,
            gdal_roughness
    output_path : os.path.abspath
        The path to write the output derivative.
    size : INT
        If a moving kernel operation, the size of the kernel
        to use.
    
    Returns
    --------
    output_path : os.path.abspath
        The path the derivative is written to, same as the
        parameter provided.
    """
    if 'gdal' in derivative:
        op = derivative.split('_')[1]
        gdal_dem_derivative(dem, output_path, op, **args)
    elif derivative == 'tpi_ocv' or derivative == 'tpi_std':
        dem_raster = Raster(dem)
        arr = dem_raster.MaskedArray.copy()
        arr.fill = dem_raster.nodata_val

        logger.info('shape of arr: {}'.format(arr.shape))
        if derivative == 'tpi_ocv':
            tpi = calc_tpi(arr, size=size)

        elif derivative == 'tpi_std':
            tpi = calc_tpi_dev(dem, size=size)

        logger.info('Writing derivative to: {}'.format(output_path))
        # Mask any originally masked pixels, this supposed to be done in calc_tpi
        # but is not working. 
        # tpi = np.ma.masked_where(arr.mask == True, tpi)
        tpi = np.where(arr.mask==True, dem_raster.nodata_val, tpi)
        dem_raster.WriteArray(tpi, output_path)
        # dem_raster.WriteArray(dem_raster.Array, '{}_arr.tif'.format(output_path[:-4]))
        # masked_int = arr.mask.astype(int)
        # print(masked_int.shape)
        # dem_raster.WriteArray(masked_int, '{}_arr_mask.tif'.format(output_path[:-4]))

        tpi = None
        arr = None
        dem_raster = None
    else:
        logger.error('Unknown derivative argument: {}'.format(derivative))


# if __name__ == '__main__':
#     supported_derivatives = ["hillshade", "slope", "aspect", "color-relief",
#                              "TRI", "TPI", "Roughness"]
#     all_derivs = ['gdal_{}'.format(x) for x in supported_derivatives]
#     all_derivs.extend(['tpi_ocv', 'tpi_std'])

#     parser = argparse.ArgumentParser()

#     parser.add_argument('dem', type=os.path.abspath,
#                         help='Path to DEM to process.')
#     parser.add_argument('output_path', type=os.path.abspath,
#                         help='Path to write output to.')
#     parser.add_argument('derivative', type=str,
#                         help='Type of derivative to create, one of: {}'.format(all_derivs))
#     parser.add_argument('-s', '--tpi_window_size', type=int,
#                         help='Size of moving kernel to use in creating TPI.')
#     parser.add_argument('-ka', '--kw_args', nargs='+',
#                         help="""Arguments to pass to gdal.DEMProcessing.
#                                 Format: "keyword:arg" "keyword2:args2" """)

#     args = parser.parse_args()

#     dem = args.dem
#     output_path = args.output_path
#     derivative = args.derivative
#     window_size = args.tpi_window_size
#     gdal_args = args.kw_args

#     # Parse gdal_args into dictionary
#     if gdal_args:
#         gdal_args = {name: value for name, value in (pair.split(':')
#                      for pair in gdal_args)}

#     dem_derivative(dem, derivative, output_path, window_size, **gdal_args)
        
        
# Topographic Roughness Index

dem = np.array([1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1],
               [1,  1,  1,  1,  1,  1,  1,  3,  9,  8],
               [1,  1,  1,  1,  1,  1,  1,  0,  1,  3],
               [1,  1,  1,  1,  1,  1,  1,  2,  9,  6],
               [1,  1,  1,  1,  1,  1,  1,  1,  1,  1])