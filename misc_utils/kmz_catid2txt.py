# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 13:55:43 2019

@author: disbr007
"""

import argparse
import logging
import geopandas as gpd
from osgeo import ogr

from id_parse_utils import write_ids


#### Logging setup
# create logger
logger = logging.getLogger('kmz_catid2txt')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def kmz_ids(kmz_path):
    driver = ogr.GetDriverByName('LIBKML')
    
    kmz_source = driver.Open(kmz_path, 0) # 0 means read-only. 1 means writeable.
    kmz_layer  = kmz_source.GetLayer()
    
    catids = []
    for feature in kmz_layer:
        desc = feature.GetField('description')
        brk = '<td>image_identifier</td>'
        catid = desc.split(brk)[1].split('<td>')[1].split('</td>')[0]
        catids.append(catid)
    
    return catids
    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kmz_path', type=str,
                        help='The path to the kmz file to write ids from.')
    parser.add_argument('out_path', type=str,
                        help='''The path of the text file to write to.''')

    args = parser.parse_args()
    
    kmz_path = args.kmz_path
    out_path = args.out_path
    
    catids = kmz_ids(kmz_path)
    logger.info('Catalog IDs found: {}'.format(len(catids)))
    write_ids(catids, out_path, ext='csv')