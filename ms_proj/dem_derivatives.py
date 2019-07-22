# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 13:52:48 2019

@author: disbr007
GDAL DEM Derivatives
"""

from osgeo import gdal
import logging, sys, os

gdal.UseExceptions()


dem = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\trans\SETSM_WV01_20160413_102001004EA97100_102001004C845700_seg1_2m_v3_trans.tif'


def dem_derivative(input_dem, derivative, array=False):
    '''
    Takes an input DEM and creates a derivative product
    input_dem: DEM
    derivate: one of "hillshade", "slope", "aspect", "color-relief", "TRI", "TPI", "Roughness"
    '''
    
    supported_derivatives = ["hillshade", "slope", "aspect", "color-relief", 
                             "TRI", "TPI", "Roughness"]
    if derivative not in supported_derivatives:
        logging.error('Unsupported derivative type. Must be one of: {}'.format(supported_derivatives))
        sys.exit()
    
    out_name = '{}_{}.tif'.format(os.path.basename(input_dem).split('.')[0], derivative)
    out_path = os.path.join(os.path.dirname(input_dem), out_name)
    
    gdal.DEMProcessing(out_path, input_dem, derivative)
    
    if array:
        from RasterWrapper import Raster
        array = Raster(out_path).Array
        
        return array
    

#slope_array = dem_derivative(dem, 'TPI', array=True)