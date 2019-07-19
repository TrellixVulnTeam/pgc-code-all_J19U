# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 10:20:36 2019

@author: disbr007

"""

from osgeo import gdal, osr, ogr
import numpy as np
import logging


class Raster():
    '''
    A class wrapper using GDAL to make simplify working with rasters.
    Basic functionality:
        -read array from raster
        -write array out with same metadata
        -sample raster at point in geocoordinates
        -sample raster with window around point
    '''
    
    def __init__(self, raster_path):
        self.data_src = gdal.Open(raster_path)
        self.geotransform = self.data_src.GetGeoTransform()
        
        self.prj = osr.SpatialReference()
        self.prj.ImportFromWkt(self.data_src.GetProjectionRef())
        
        self.x_sz = self.data_src.RasterXSize
        self.y_sz = self.data_src.RasterYSize
        self.nodata_val = self.data_src.GetRasterBand(1).GetNoDataValue()
        self.dtype = self.data_src.GetRasterBand(1).DataType
        
        ## Get the raster as an array
        self.Array = self.data_src.ReadAsArray()


    def WriteArray(self, array, out_path):
        '''
        Writes the passed array with the metadata of the current raster object
        as new raster.
        '''
        fmt = 'GTiff'
        driver = gdal.GetDriverByName(fmt)
        dst_ds = driver.Create(out_path, self.x_sz, self.y_sz, 1, self.dtype)
        dst_ds.GetRasterBand(1).WriteArray(array)
        dst_ds.SetGeoTransform(self.geotransform)
        dst_ds.SetProjection(self.prj.ExportToWkt())
        dst_ds.GetRasterBand(1).SetNoDataValue(self.nodata_val)
        
        dst_ds = None
        
        
    def SamplePoint(self, point):
        '''
        Samples the current raster object at the given point. Must be the
        sampe coordinate system used by the raster object.
        point: tuple of (y, x) in geocoordinates
        '''
        ## Convert point geocoordinates to array coordinates
        py = int(np.around((point[0] - self.geotransform[3]) / self.geotransform[5]))
        px = int(np.around((point[1] - self.geotransform[0]) / self.geotransform[1]))
        print(px, py)
        ## Handle point being out of raster bounds
        try:    
            point_value = self.Array[py, px]
        except IndexError as e:
            logging.error('Point not within raster bounds.')
            logging.error(e)
            point_value = None
        return point_value
    
    
    def SampleWindow(self, center_point, window_size, agg='mean'):
        '''
        Samples the current raster object using a window centered 
        on center_point.
        center_point: tuple of (y, x) in geocoordinates
        window_size: tuple of (y_size, x_size) as number of pixels (must be odd)
        agg: type of aggregation, default is mean, can also me sum, min, max'''
        
        ## Convert point geocoordinates to array coordinates
        py = int(np.around((center_point[0] - self.geotransform[3]) / self.geotransform[5]))
        px = int(np.around((center_point[1] - self.geotransform[0]) / self.geotransform[1]))
        
        ## Get window arround center point
        # Get size in y, x directions
        y_sz = window_size[0]
        y_step = int(y_sz / 2)
        x_sz = window_size[1]
        x_step = int(x_sz / 2)
        
        # Get pixel locations of window bounds
        ymin = py - y_step
        ymax = py + y_step + 1 # slicing doesn't include stop val so add 1
        xmin = px - x_step
        xmax = px + x_step + 1 
        
        ## Handle window being out of raster bounds
        try:
            window = self.Array[ymin:ymax, xmin:xmax]
            agg_lut = {
                'mean': window.mean(),
                'sum': window.sum(),
                'min': window.min(),
                'max': window.max()
                }

            window_agg = agg_lut[agg]
            
        except IndexError as e:
            logging.error('Window bounds not within raster bounds.')
            logging.error(e)
            window_agg = None
            
        return window_agg
