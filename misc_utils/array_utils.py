# -*- coding: utf-8 -*-
"""
Created on Sat Feb 15 12:14:14 2020

@author: disbr007
"""
import logging
import numpy as np
from scipy import interpolate

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def interpolate_nodata(array, method):
    """
    array : np.ndarray
        Array containing either masked values or np.NaN's to
        be interpolated
    method : STR
        Interpolation method, one of: 'cubic', 'nearest', 'linear'

    Returns
    np.ndarray
        Note: not np.ma.core.MaskedArray
    """
    # Create a vector of column indicies
    x = np.arange(0, array.shape[1])
    # Create a vector row indicies
    y = np.arange(0, array.shape[0])
    # Create grids of coordinate matrices from coordinate vectors,
    # these are the points at which to interpolate data
    xx, yy = np.meshgrid(x, y)
    # mask invalid values
    array = np.ma.masked_invalid(array)
    # get the coordinates of valid values
    x1 = xx[~array.mask]
    y1 = yy[~array.mask]
    # Get the array of only valid values
    newarr = array[~array.mask]
    
    
    interp_arr = interpolate.griddata(points=(x1, y1), 
                                      values=newarr.ravel(),
                                      xi=(xx, yy),
                                      method=method)
    
    return interp_arr