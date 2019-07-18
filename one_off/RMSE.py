# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 12:00:54 2019

@author: disbr007
"""

import numpy as np
from osgeo import ogr, gdal, osr
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, Point
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import random, argparse, os, logging


def calc_rmse(l1, l2):
    '''
    Calculates RMSE of two lists of numbers.
    '''

    diffs = [x - y for x, y in zip(l1, l2)]
    sq_diff = [x**2 for x in diffs]
    mean_sq_diff = sum(sq_diff) / len(sq_diff)
    rmse_val = np.sqrt(mean_sq_diff)
    
    return rmse_val


#def raster_bounds(path):
    '''
    GDAL only version of getting bounds
    '''
#    src = gdal.Open(path)
#    gt = src.GetGeoTransform()
#    minx = gt[0]
#    maxy = gt[3]
#    maxx = minx + gt[1] * src.RasterXSize
#    miny = maxy + gt[5] * src.RasterYSize
#    
#    return minx, miny, maxx, maxy
    

def raster_bounds(path):
    '''
    Gets boundary of raster at path, ignoring no data values
    '''
    print('Getting raster bounds...')
    with rasterio.drivers():
        with rasterio.open(path) as src:
            # Raster band
            rb = src.read(1)
            nodata = src.nodatavals[0]
            # Array of 1's and 0's
            binary = np.where(rb <= nodata, 0, 1)
            # Array True, False
            mask = np.where(binary == 1, True, False)
            ## Create a dictionary of raster values and geometries, where 
            ## the geometries are based on grouping the values in the binary array
            ## and ignoring the False values in the mask
            geoms = list(({'properties': {'raster_val': value}, 'geometry': shp} 
            for i, (shp, value) in enumerate(shapes(binary, mask=mask, transform=src.affine))))
            bb = shape(geoms[0]['geometry'])
    return bb


def random_points_within(num_points, poly1, poly2):
    '''
    Creates num_points with the boundaries of poly1 and poly2,
    returns a list of shapely Points
    '''
    print('Creating random points...')
    min_x1, min_y1, max_x1, max_y1 = poly1.bounds
    min_x2, min_y2, max_x2, max_y2 = poly2.bounds
    
    min_x = max(min_x1, min_x2)
    min_y = max(min_y1, min_y2)
    max_x = min(max_x1, max_x2)
    max_y = min(max_y1, max_y2)
    
    points = []

    while len(points) < num_points:
        random_point = Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)])
        if (random_point.within(poly1) and random_point.within(poly2)):
            points.append(random_point)

    return points


def sample_points(dem1_path, dem2_path, num_pts=1000):
    '''
    Samples num_pts from dem1 and dem2 and returns a dataframe of values, as well as 
    difference of dem1 - dem2
    '''
    # Read as array
    dem1_src = gdal.Open(dem1_path)
#    dem1_nodata = dem1_src.GetRasterBand(1).GetNoDataValue()
    dem1 = dem1_src.ReadAsArray()
    dem1_gt = dem1_src.GetGeoTransform()
            
    dem2_src = gdal.Open(dem2_path)
#    dem2_nodata = dem2_src.GetRasterBand(1).GetNoDataValue()
    dem2 = dem2_src.ReadAsArray()
    dem2_gt = dem2_src.GetGeoTransform()
    
    
    ## Get extents of DEMs exluding NoData
    dem1_bb = raster_bounds(dem1_path)
    dem2_bb = raster_bounds(dem2_path)
#    bb_gdf = gpd.GeoDataFrame(geometry=[dem1_bb, dem2_bb])
#    bb_gdf.to_file(r'V:\pgc\data\scratch\jeff\brash_island\dem\pc_align\dem_bb.shp', driver='ESRI Shapefile')
            
    
    ## Generate random points within data extents of DEMs
    random_pts = random_points_within(num_pts, dem1_bb, dem2_bb)
    
    geoms = []
    dem1_vals = []
    dem2_vals = []
    differences = []
    
    ## Sample z-values of DEMs at both points
    for i, pt in enumerate(random_pts):
        # Determine pixel locations using DEM Geotransform 
        px1 = int((pt.x - dem1_gt[0]) / dem1_gt[1])
        py1 = int((pt.y - dem1_gt[3]) / dem1_gt[5])
        
        px2 = int((pt.x - dem2_gt[0]) / dem2_gt[1])
        py2 = int((pt.y - dem2_gt[3]) / dem2_gt[5])
        
        
        dem1_val = dem1[py1][px1]
        dem2_val = dem2[py2][px2]
        
        diff = dem1_val - dem2_val
        
        # Append to list for creating geodataframe
        geoms.append(Point(pt.x, pt.y))
        dem1_vals.append(dem1_val)
        dem2_vals.append(dem2_val)
        differences.append(diff)
    
    print('Final number of sample points (ignoring NoData pts): {}'.format(len(differences)))
    ## Create geodataframe of points with elevation 1, elevation 2, and difference
    gdf = gpd.GeoDataFrame({'DEM1_value':dem1_vals, 'DEM2_value':dem2_vals, 'Diff':differences},
                           geometry=geoms)
    
    return gdf


def normalize(vals, norm_min, norm_max):
    '''
    Normalizes a list of values to be between norm_min and norm_max
    '''
    normalized = []
    
    vals_min = min(vals)
    vals_max = max(vals)
    
    for v in vals:
#        z = (v - vals_min) / (vals_max - vals_min)
        z = (norm_max - norm_min)/(vals_max - vals_min) * (v - vals_min) + norm_min
        normalized.append(z)
    
    return normalized


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dem1_path', type=str,
                        help='Path to the first DEM.')
    parser.add_argument('dem2_path', type=str,
                        help='Path to the second DEM.')
    parser.add_argument('-n', '--num_pts', type=int,
                        help='Number of sample points to use for sampling and RMSE calculation. Default 1000')
    parser.add_argument('-p', '--plot', type=str,
                        help='Option path to save plots: histogram of differences, scatter of values, map of sample points')
    parser.add_argument('-w', '--write_shp', type=str,
                        help='Optional path to write shapefile of sample points')
    
    args = parser.parse_args()
    
    
    # Default 1000 sample points
    num_pts = args.num_pts if args.num_pts else 1000

    # Sample DEMs at random points
    gdf = sample_points(args.dem1_path, args.dem2_path, num_pts=num_pts)

    ## Calculate RMSE
    rmse_val = calc_rmse(list(gdf['DEM1_value']), list(gdf['DEM2_value']))    
    print('\nRMSE: {:.3}'.format(rmse_val))
    
    if args.write_shp:
        shp_path = os.path.abspath(args.write_shp)
        gdf.to_file(shp_path, driver='ESRI Shapefile')
    
    if args.plot:
        #### Plot
        plt.style.use('ggplot')
        fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(14,8))
        fig.suptitle('RMSE: {:.3f}'.format(rmse_val))
        
        ## Histogram of differences
        hist = gdf['Diff'].hist(bins=25, ax=axes[0], edgecolor='w')
        axes[0].set_yscale('log')
        axes[0].set_xlabel('Elevation Difference')
        
        ## Scatter plot of DEM1 vs DEM2
        gdf[['DEM1_value', 'DEM2_value']].plot(x='DEM1_value', y='DEM2_value', kind='scatter', ax=axes[1], s=0.5)
        # Match x and y limits and scale
        axes[1].set_aspect('equal', adjustable='box')
        min_val = min([gdf['DEM1_value'].min(), gdf['DEM2_value'].min()])
        max_val = max([gdf['DEM1_value'].max(), gdf['DEM2_value'].max()])
        axes[1].set_xlim([min_val, max_val])
        axes[1].set_ylim([min_val, max_val])
        
        ## Map of absolute differences
        cmap ='RdYlGn_r'
        gdf['abs_diff'] = abs(gdf['Diff'])
        gdf.sort_values(by='abs_diff', inplace=True)
        gdf.plot(column='abs_diff', cmap=cmap, markersize=normalize(gdf['abs_diff'], 0, 10), 
                 alpha=1, ax=axes[2])

        axes[2].set_xticklabels([])
        axes[2].set_yticklabels([])
        
        #for ax in axes:
        #    ax.set(adjustable='box-forced', aspect='equal')
        plt.tight_layout()
        plt.show()
        plot_path = os.path.abspath(args.plot)
#        plt.savefig(plot_path)
        
        
        