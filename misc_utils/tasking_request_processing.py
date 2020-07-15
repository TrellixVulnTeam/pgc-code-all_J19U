# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 14:50:14 2019

@author: disbr007
"""
import argparse
import os

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from coord_converter import remove_symbols
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh')


def process_tasking(xlsx, out_name):
    '''
    Takes an excel workbook with a sheet named 'Targets' and converts the latitude and longitude points into a shapefile.
    Also write out a renamed excel file.
    xlsx: path to excel file
    out_name: name according to convention [first_initial][last_name][award_number][year] e.g.: bsmith_123456_2019-20
    '''
    # Read excel as pandas dataframe, store original column names for writing out
    logger.info("Reading excel sheet...")
    request = pd.read_excel(xlsx, sheet_name='Targets', dtype=str)
    cols = list(request)

    # Remove any degrees symbols
    request = remove_symbols(request)
    # Convert to geopandas database, using shapely Points
    logger.info('Converting to shapefile...')
    geometry = [Point(y,x) for y, x in zip(request['Longitude (decimal degrees)'].astype(float),
                                           request['Latitude (decimal degrees)'].astype(float))]
    geo_req = gpd.GeoDataFrame(request, geometry=geometry, crs='epsg:4326')
    geo_req.fillna(0, inplace=True)

    # Write out shapefile
    # Convert datetime columns to strings
    out_shp = os.path.join(os.path.dirname(xlsx), '{}.shp'.format(out_name))
    # for col in list(geo_reg.select_dtypes(include=np.datetime64)):
    # 	geo_req[col] = geo_req[col].dt.strfrtime('%b/%d/%Y')

    logger.info('Writing to: {}'.format(out_shp))
    geo_req.to_file(out_shp, driver='ESRI Shapefile')
    # Write out renamed excel file
    request = request[cols]
    request.to_excel(os.path.join(os.path.dirname(xlsx), '{}_request.xlsx'.format(out_name)))

    return request


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('xlsx', type=str, help='Input excel file, containing "Targets" sheet with coordinates.')
    parser.add_argument('out_name', type=str, help="""Name of shapefile and excel sheet to write.\n
                        (user's first initial)(user's last name)_(Award Number or Affiliation)_Year
                        Example: edeeb_CRELL_2019-20""")
    args = parser.parse_args()

    process_tasking(args.xlsx, args.out_name)
