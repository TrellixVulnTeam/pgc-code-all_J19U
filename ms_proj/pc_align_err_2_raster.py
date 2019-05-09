# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 15:27:16 2019

@author: disbr007
"""

import gdal
from osgeo import ogr, osr
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import matplotlib as mpl
#from rasterio.profiles import DefaultGTiffProfile
#from rasterio.features import rasterize
#from rasterio.transform import IDENTITY
import numpy as np
#import rasterio
import copy, os



def error_gpd(error_csv):
    '''
    Reads a csv of alignment errors and returns a geodataframe of point errors
    '''    
    ## Read end errors into pandas
    end_err = pd.read_csv(error_csv)
    # Projection information stored in second row of csv
    projection = end_err['# latitude'].iloc[1].split('Projection: ')[1]
    
    # First two rows contain metadata - drop
    end_err = end_err.drop([0, 1])
    
    end_err.rename(columns={'# latitude': 'latitude'}, inplace=True)
    end_err['latitude'] = end_err['latitude'].astype('float64')
    points = end_err.apply(lambda row: Point(row.longitude, row.latitude), axis=1)
    
    ## Convert to a geopandas geodataframe
    #geometry = list(end_err['Coordinates'])
    err = gpd.GeoDataFrame(end_err, geometry=points)
    err.crs = {'init': 'epsg:4326'}
    schema = {
            'geometry': 'Point',
            'properties':{
                    'latitude': 'float',
                    'longitude': 'float',
                    'height above datum (meters)': 'float',
                    'error (meters)': 'float'
                    }
            }
    return err


error_files = [r"V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\WV02_20140614\WV02_20140614_-beg_errors.csv",
               r"V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\WV02_20140614\WV02_20140614_-end_errors.csv",
               r"V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\WV02_20170605\WV02_20170605_run-beg_errors.csv",
               r"V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\WV02_20170605\WV02_20170605_run-end_errors.csv"]

#for csv in error_files:
#    df = error_gpd(csv)
#    print(csv)
#    print(df['error (meters)'].min())
#    print(df['error (meters)'].max())   
#    print(df['error (meters)'].mean())
#    sample_df = df.sample(frac=0.5)
#    outname = os.path.join(os.path.dirname(csv), '{}50p.shp'.format(os.path.basename(csv).split('.')[0]))
#    sample_df.to_file(outname, driver='ESRI Shapefile')
#

## Plotting
position_counter = 0
fig, axs = plt.subplots(nrows=2, ncols=2)
axs = axs.ravel()
min_err = 9999
max_err = 0

for i in range(4):
    f = error_files[position_counter]
    gdf = error_gpd(f)
#    if i in (1, 3):
#    gdf.sort_values('error (meters)', ascending=True, inplace=True)
#    gdf.reset_index(drop=True, inplace=True)
#    number_rows = len(gdf) 
#    p75 = int((len(gdf) * 0.75) - 1) # num rows that is 75 percent
#    gdf = gdf.iloc[p75:]
    att = gdf['error (meters)']
    print(error_files[position_counter],'\nMean: {}\nMin: {}\nMax: {}'.format(att.mean(), att.min(), att.max()))
    outname = os.path.join(os.path.dirname(f), '{}{}_v2.shp'.format(os.path.basename(f).split('.')[0], i))
    gdf.to_file(outname, driver='ESRI Shapefile')
    
    # Get min and max for cbar normalizing
    if att.min() < min_err:
        min_err = att.min()
    if att.max() > max_err:
        max_err = att.max()
        
    cmap='RdYlGn_r'
    ax = axs[i]
    ax.set_facecolor('#d8dcd6')
    ax.set_title(os.path.basename(error_files[position_counter]).split('.')[0])
    err_plot = gdf.plot(ax=ax, markersize=0.5, c=att, cmap=cmap)
    position_counter += 1

norm = mpl.colors.Normalize(vmin=min_err, vmax=max_err)
cax = fig.add_axes([0.95, 0.2, 0.02, 0.6])
cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, spacing='proportional')




#test = err.iloc[0:1000]
#test.to_file(r'V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\test\test.shp', schema=schema, driver='ESRI Shapefile')
#
##polar_ster = {'init':'epsg:3995'}
##err.geometry = err.geometry.to_crs(polar_ster)
##err.crs = polar_ster
#
#src = ogr.Open(err.to_json(), 0)
#src_layer = src.GetLayer()
#
#out_tif = r'C:\Users\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\WV02_2017_end_err.tif'
#
#cols=6122
#rows=5058
#
#with rasterio.Env():
#    shapes = ((geom, value) for geom, value in zip(err.geometry, err['error (meters)']))
#    burned = rasterize(shapes=shapes, out_shape=(cols, rows), fill=-9999, dtype='float64')
#    with rasterio.open(
#            out_tif,
#            'w',
#            driver='GTiff',
#            width=cols,
#            height=rows,
#            count=1,
#            dtype=np.float64,
#            nodata=-9999.0,
#            transform=IDENTITY,
#            crs=err.crs) as out:
#        out.write(burned, indexes=1)
        


#with rasterio.open(r'C:\Users\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\WV02_2017_end_err.tif', 
#                   'w+',
#                   driver='GTiff',
#                   width=cols,
#                   height=rows,
#                   count=1,
#                   nodata=-9999.0,
#                   transform=IDENTITY,
#                   crs=err.crs) as out:
##    out_arr = out.read(1)
#    shapes = ((geom, value) for geom, value in zip(err.geometry, err['error (meters)']))
#    burned = rasterize(shapes=shapes, out_shape=(cols, rows), fill=-9999, dtype='float64')
#    out.write(burned, 1)
