# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 13:55:43 2019

@author: disbr007
"""
import argparse
import os
import re
from zipfile import ZipFile

import geopandas as gpd
from osgeo import ogr
from shapely import wkt

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

if __name__ == '__main__':
    parser = argparse.ArgumentParser('Create shapefile of catalogids from KMZ exported from discover.digital.globe')

    parser.add_argument('-kmz', type=os.path.abspath, help='Path to kmz exported from DG Discover.')
    parser.add_argument('-o', '--out_shp', type=os.path.abspath, help='Path to shapefile to write.')

    args = parser.parse_args()

    kmz_p = args.kmz
    out_shp = args.out_shp


    if kmz_p.endswith('.kmz'):
        logger.info('Extracting KMZ to KML...')
        filename = os.path.basename(os.path.splitext(kmz_p)[0])
        unzip_dir = os.path.join(os.path.dirname(kmz_p), filename)
        if not os.path.isdir(unzip_dir):
            os.makedirs(unzip_dir)
        with ZipFile(kmz_p, 'r') as zr:
            zr.extractall(unzip_dir)
        kml_p = os.path.join(unzip_dir, 'doc.kml')
    else:
        kml_p = kmz_p

    logger.info('Reading source KML: {}'.format(kml_p))
    driver = ogr.GetDriverByName('KML')
    kmz_source = driver.Open(kml_p, 0)  # 0 means read-only. 1 means writeable.
    kmz_layer  = kmz_source.GetLayer()
    lyr_defn   = kmz_layer.GetLayerDefn()

    fields = []
    for i in range(lyr_defn.GetFieldCount()):
        fields.append(lyr_defn.GetFieldDefn(i).GetName())

    id_re = re.compile("<td>image_identifier</td> <td>([a-zA-Z0-9]*)</td>")

    logger.info('Parsing KML file...')
    catids = []
    geoms = []
    for feature in kmz_layer:
        geom = feature.geometry().ExportToWkt()
        geoms.append(geom)

        desc = feature.GetField('Description')
        cid = id_re.search(desc).group(1)
        catids.append(cid)

    gdf = gpd.GeoDataFrame({'catalogids': catids, 'geometry': geoms}, crs=4326)
    gdf['geometry'] = gdf['geometry'].apply(wkt.loads)

    logger.info('Writing to shapefile...')
    gdf.to_file(out_shp)
