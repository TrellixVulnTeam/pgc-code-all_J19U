# -*- coding: utf-8 -*-
"""
Created on Tue May  7 10:27:56 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from osgeo import gdal,ogr
import struct, os

import matplotlib.pyplot as plt
import seaborn as sns


def merge_gdf(gdf1, gdf2):
    gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True), crs=gdf1.crs)
    return gdf


def line2pts(poly, interval, write_path=False):
    '''
    takes a geodataframe that has line geometry and returns points along the 
    line at the specified interval, where interval is a fraction of the line length
    poly: geodataframe with line geometry
    interval: fraction of length of line to create points at
    '''
    nodes = gpd.GeoDataFrame(columns=['pts'])
    location = 0.0
    for i in np.arange(0.0, 1.0, interval):
        node = gpd.GeoDataFrame(columns=['pts'])
        pt = poly.geometry.interpolate(i, normalized=True)
        node['pts'] = pt
        node['location'] = location
        location += interval
        nodes = merge_gdf(nodes, node)
    
    nodes.set_geometry('pts', inplace=True)
    nodes.crs = poly.crs
    if write_path:
        driver = 'ESRI Shapefile'
        nodes.to_file(write_path, driver=driver)
    return nodes

def plot_sample_locations(line_shp, raster, label=None):
    driver = 'ESRI Shapefile'
#    sample_line_path = r'E:\disbr007\umn\ms_proj\data\DEM_diff\sample_line.shp'
    sample_line_path = line_shp
    sample_line = gpd.read_file(sample_line_path, driver=driver)
    
#    pts_path = r'E:\disbr007\umn\ms_proj\data\DEM_diff\sample_pts.shp'
    pts_path = os.path.join(os.path.dirname(sample_line_path), '{}_sample_pts.shp'.format(os.path.basename(sample_line_path)))
    sample_pts = line2pts(sample_line, 0.005, write_path=pts_path)
        
#    src_filename = r'E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\2m_reclip\gdal_calc.tif'
    shp_filename = pts_path
    
    src_ds = gdal.Open(raster) 
    gt = src_ds.GetGeoTransform()
    rb = src_ds.GetRasterBand(1)
    
    ds = ogr.Open(shp_filename)
    lyr = ds.GetLayer()
    
    sampled_locations = []
    sampled_vals = []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        mx,my = geom.GetX(), geom.GetY()  #coord in map units
    
        #Convert from map to pixel coordinates.
        #Only works for geotransforms with no rotation.
        px = int((mx - gt[0]) / gt[1]) #x pixel
        py = int((my - gt[3]) / gt[5]) #y pixel
    
        structval = rb.ReadRaster(px, py, 1, 1, buf_type=gdal.GDT_Float32) #Assumes 16 bit int aka 'short'
#        print(structval)
        intval = struct.unpack('f' , structval) #use the 'short' format code (2 bytes) not int (4 bytes)
        
        pt_location = feat.GetField('location')
        sampled_locations.append(pt_location)
        sampled_vals.append(intval[0])
#        print(intval[0]) #intval is a tuple, length=1 as we only asked for 1 pixel value
    
    df = pd.DataFrame(list(zip(sampled_locations, sampled_vals)), columns=['location', 'value'])
#    df.plot(x='location', y='value', c='value', linestyle='-', marker='o', markersize=1, label=label, ax=ax)
    plt.plot('location', 'value', data=df, linestyle='-', marker='o', markersize=1.5, label=label)
    

gdal_calc = r'E:\disbr007\umn\ms_proj\data\DEM_diff\gdal_calc_UTM.tif'
gdal_calc2 = r'E:\disbr007\umn\ms_proj\data\DEM_diff\gdal_calc_UTM_v2.tif'
dem_2017 = r'E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\masked\WV02_2017_DEM_masked_trans_prj_sftZ.tif'
dem_2014 = r'E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\masked\WV02_2014_DEM_masked_trans_prj.tif'

sample_line_path = r'E:\disbr007\umn\ms_proj\data\DEM_diff\sample_line_UTM.shp'    


fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True)
plt.sca(ax1)
plot_sample_locations(sample_line_path, dem_2014, label='2014')
plot_sample_locations(sample_line_path, dem_2017, label='2017')
plt.xlabel('Location along sample line (percentage)')
plt.legend()
plt.sca(ax2)
plot_sample_locations(sample_line_path, gdal_calc, label='DEM of Diff')
#plot_sample_locations(sample_line_path, gdal_calc2, label='DEM of Diff2')
plt.xlabel('Location along sample line (percentage)')
plt.ylabel('Elevation')
plt.legend()