# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 13:52:48 2019

@author: disbr007
GDAL DEM Derivatives
"""

## Standard Libs
import argparse
import logging, os, sys
import numpy as np

## Third Party Libs
import cv2
from osgeo import gdal
from scipy.ndimage.filters import generic_filter

## Local libs
from misc_utils.RasterWrapper import Raster
from logging_utils import create_logger


gdal.UseExceptions()
logger = create_logger('dem_derivatives.py', 'sh')


def gdal_dem_derivative(input_dem, output_path, derivative, return_array=False, *args):
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


    gdal.DEMProcessing(output_path, input_dem, derivative, *args)

    if return_array:
        from RasterWrapper import Raster
        array = Raster(output_path).Array

        return array


def calc_tpi(dem, size, nodata_val):
    """
    OpenCV implementation of TPI
    dem: array
    size: int, kernel size in x and y directions (square kernel)
    Note - borderType determines handline of edge cases. REPLICATE will take the outermost row and columns and extend
    them as far as is needed for the given kernel size.
    """
    kernel = np.ones((size,size),np.float32)/(size*size)
    # -1 indicates new output array
    dem_conv = cv2.filter2D(dem, -1, kernel, borderType=cv2.BORDER_REPLICATE)
    tpi = dem - dem_conv
    
    # Set pixels affected by border to NoData
    # First and last rows
    tpi[0:size, :] = nodata_val
    tpi[-size:, :] = nodata_val
    # First and last cols
    tpi[:, 0:size] = nodata_val
    tpi[:, -size:] = nodata_val
    
    return tpi


def calc_tpi_dev(dem, size, nodata_val):
    """
    Based on (De Reu 2013)
    Calculates the tpi/standard deviation of the kernel to account for surface roughness.
    dem: array
    size: int, kernel size in x and y directions (square kernel)
    """
    tpi = calc_tpi(dem, size, nodata_val)
    # Calculate the standard deviation of each cell, mode='nearest' == cv2.BORDER_REPLICATE
    std_array = generic_filter(dem, np.std, size=size, mode='nearest')

    tpi_dev = tpi / std_array

    return tpi_dev


def dem_derivative(dem, derivative, output_path, size):
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
            gdal_color-relief, gdal_tri, gdal_tri,
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
        gdal_dem_derivative(dem, output_path, op)
    elif derivative == 'tpi_ocv' or derivative == 'tpi_std':
        dem_raster = Raster(dem)
        arr = dem_raster.Array
        
        if derivative == 'tpi_ocv':
            tpi = calc_tpi(arr, size=size, nodata_val=dem_raster.nodata_val)

        elif derivative == 'tpi_std':
            tpi = calc_tpi_dev(dem, size=size, nodata_val=dem_raster.nodata_val)
        
        dem_raster.WriteArray(tpi, output_path)
        tpi = None
        arr = None
        dem_raster = None
    else:
        logger.error('Unknown derivative argument: {}'.format(derivative))


# prj_dir = r'E:\disbr007\umn\ms'
# dem_dir = os.path.join(prj_dir, 'dems')
# dem_p = os.path.join(dem_dir, r'aoi_2\test\WV02_20160312_1030010051B3C500_10300100526C3C00_seg1_2m_demclip_test.tif')
# aoi_2 = os.path.join(dem_dir, 'aoi_2')
# tpi_dir = os.path.join(aoi_2, 'tpi')
# dem_filename = os.path.basename(dem_p)
# dem_name = dem_filename.split('.')[0]
# size = 201
# tpi_filename = '{}_tpi{}.tif'.format(dem_name, size)
# out_tpi = os.path.join(tpi_dir, tpi_filename)
# dem_raster = Raster(dem_p)
# arr = dem_raster.Array
# tpi = calc_tpi(arr, size=size, no_data_val=dem_raster.nodata_val)
# dem_raster.WriteArray(tpi, out_tpi)        

            
if __name__ == '__main__':
    supported_derivatives=["hillshade", "slope", "aspect", "color-relief", 
                              "TRI", "TPI", "Roughness"]
    all_derivs = ['gdal_{}'.format(x) for x in supported_derivatives]
    all_derivs.append('tpi')
    parser = argparse.ArgumentParser()

    parser.add_argument('dem', type=os.path.abspath,
                          help='Path to DEM to process.')
    parser.add_argument('output_path', type=os.path.abspath,
                          help='Path to write output to.')
    parser.add_argument('derivative', type=str,
                          help='Type of derivative to create, one of: {}'.format(all_derivs))
    parser.add_argument('-s', '--tpi_window_size', type=int,
                          help='Size of moving kernel to use in creating TPI.')

    args = parser.parse_args()

    dem = args.dem
    output_path = args.output_path
    derivative = args.derivative
    window_size = args.tpi_window_size

    dem_derivative(dem, derivative, output_path, window_size)