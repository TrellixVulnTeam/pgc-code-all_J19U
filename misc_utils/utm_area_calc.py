# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:03:31 2019

@author: disbr007
"""
import copy
import math
import numpy as np

import geopandas as gpd
import pandas as pd
import tqdm
from fiona.crs import from_epsg, from_string

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def area_calc(geodataframe, area_col='area_sqkm', units='sqkm', polar=True):
    gdf = copy.deepcopy(geodataframe)

    src_geom_name = gdf.geometry.name
    src_crs = gdf.crs
    src_cols = list(gdf)
    src_cols.append(area_col)

    epsg_col = 'epsg_col'
    gdf[epsg_col] = gdf.geometry.centroid.apply(lambda x: find_epsg(x))

    gdf_area = gpd.GeoDataFrame()
    for epsg, df in gdf.groupby(epsg_col):
        logger.debug('Calculating areas for epsg: {}, Features: {}'.format(epsg, len(df)))
        reprj = df.to_crs('epsg:{}'.format(epsg))
        if units == 'sqkm':
            reprj[area_col] = reprj.geometry.area / 10e5
        elif units == 'sqm':
            reprj[area_col] = reprj.geometry.area
        else:
            logger.error('Unrecognized units argument: {}'.format(units))

        reprj = reprj.to_crs(src_crs)

        gdf_area = pd.concat([gdf_area, reprj])

    gdf_area = gdf_area[src_cols]

    return gdf_area



def find_epsg(point):
    if point.y >= 60:
        epsg = "3413"
    elif point.y <= -60:
        epsg = "3031"
    else:
        zone_number = int(math.ceil((point.x + 180) / 6))
        if point.y <= 0:
            epsg = "327{}".format(str(zone_number).zfill(2))
        else:
            epsg = "326{}".format(str(zone_number).zfill(2))

    return epsg
