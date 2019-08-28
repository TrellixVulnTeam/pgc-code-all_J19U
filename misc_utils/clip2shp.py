# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:36:40 2019

@author: disbr007
Clip raster to shapefile extent. Must be in the same projection.
"""

from osgeo import ogr, gdal, osr
import os, logging, argparse


gdal.UseExceptions()
ogr.UseExceptions()


def translate_rasters(rasters, projWin, out_dir, out_suffix='_trans'):
    '''
    Takes a list of rasters and translates (clips) them to the minimum bounding box
    '''
    ## Translate (clip) to minimum bounding box
    translated = {}
    for raster_p in rasters:
        if not out_dir:
            out_dir == os.path.dirname(raster_p)
        logging.info('Translating {}...'.format(raster_p))
        raster_out_name = '{}_{}.tif'.format(os.path.basename(raster_p).split('.')[0], out_suffix)
        raster_op = os.path.join(out_dir, raster_out_name)
        
        raster_ds = gdal.Open(raster_p)
        translated[raster_out_name] = gdal.Translate(raster_op, raster_ds, projWin=projWin)
    
    return translated


def get_shp_bounds(shp_path):
    '''
    Get the bounds of a shapefile. Will return bounds of all features.
    '''
    data_source =  ogr.Open(shp_path, 0)
    layer = data_source.GetLayer()
#    x_min, x_max, y_min, y_max = layer.GetExtent()
    ulx, lrx, lry, uly = layer.GetExtent()
    ## Ordered for gdal_translate
    projWin = [ulx, uly, lrx, lry]
    
    del layer    
    del data_source

    for c in projWin:
        print(c)
    return projWin


def translate(shp_path, rasters, out_dir, out_suffix='_trans'):
    '''
    Wrapper function.
    '''
    projWin = get_shp_bounds(shp_path)
    translate_rasters(rasters, projWin=projWin, out_dir=out_dir, out_suffix=out_suffix)
    
#
#if __name__ == '__main__':
#    parser = argparse.ArgumentParser()
#    
#    parser.add_argument('shape_path', type=str, help='Shape to clip rasters to.')
#    parser.add_argument('rasters', nargs='*', help='Rasters to clip.')
#    parser.add_argument('out_dir', type=str, help='Director to write clipped rasters to.')
#    parser.add_argument('--out_suffix', type=str, help='Suffix to add to clipped rasters.')
#    
#    args = parser.parse_args()
    
#    print(args)
#    
#    shp_path = args.shape_path
#    rasters = args.rasters
#    out_dir = args.out_dir
#    out_suffix = args.out_suffix
#    
#    translate(shp_path, rasters, out_dir, out_suffix)
#    

translate(r'E:\disbr007\tarfala\storg_bounds_prj.shp', 
          [r'E:\disbr007\tarfala\dems\WV01_20140528_10200100306AFE00_102001002D1E8A00_2m\WV01_20140528_10200100306AFE00_102001002D1E8A00_seg1_2m_dem.tif'],
          r'E:\disbr007\tarfala\dems_storg', 
          'storg')