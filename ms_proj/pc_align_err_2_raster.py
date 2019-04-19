# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 15:27:16 2019

@author: disbr007
"""

import pandas as pd
import geopandas
from shapely.geometry import Point
import matplotlib.pyplot as plt
from rasterio.profiles import DefaultGTiffProfile
from rasterio.features import rasterize
import numpy as np
import rasterio
import copy, os

# Read end errors into pandas
end_err = pd.read_csv(r"V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\run\WV02_20170605_run-end_errors.csv")

# Projection information stored in second row of csv
projection = end_err['# latitude'].iloc[1].split('Projection: ')[1]

# First two rows contain metadata - drop
end_err = end_err.drop([0, 1])

# Convert latitude column type
end_err['# latitude'] = end_err['# latitude'].astype('float64')
# Add coordinates column by combining latitude and longitude
end_err['Coordinates'] = list(zip(end_err['longitude'], end_err['# latitude'].astype('float64')))

# Convert to shapely geometry
end_err['Coordinates'] = end_err['Coordinates'].apply(Point)

# Convert to a geopandas geodataframe
end_err = geopandas.GeoDataFrame(end_err, geometry='Coordinates', crs=projection)

test = end_err.iloc[0:100]
test.to_file(r'V:\pgc\data\scratch\jeff\2019apr19_umiat_detach_zone\run\test.shp')

# Create an empty raster to write to
out_meta = {
        'driver': 'GTiff',
        'count': 1,
        'dtype': 'float64',
        'blockxsize': 50,
        'blockysize': 50,
        'nodata': -9999.0,
        'width': 5800,
        'height': 5800,
        'crs': projection
        }


with rasterio.open('./end_err.tif', 'w+', **out_meta) as out:
    out_arr = out.read(1)
    shapes = ((geom, value) for geom, value in zip(end_err.geometry, end_err['error (meters)']))
    burned = rasterize(shapes=shapes, fill=-9999, out=out_arr, transform=out.transform)
    