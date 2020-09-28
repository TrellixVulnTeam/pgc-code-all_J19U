import argparse
import os
from pathlib import Path

import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import dissolve_gdf

logger = create_logger(__name__, 'sh', 'INFO')

shps = [r'E:\disbr007\umn\2020sep27_eureka\img\WV02_20110811220642_103001000C5D4600_11AUG11220642-P1BS-052838905080_01_P002.shp',
        r'E:\disbr007\umn\2020sep27_eureka\img\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-500287602150_01_P009_fp.shp']

def intersect_aois(shps):
    logger.info('Finding intersection among provided polygons...')
    logger.info('Reading: {}'.format(shps[0]))
    shp = gpd.read_file(shps[0])
    if len(shp) > 1:
        shp = dissolve_gdf(shp)
    for s in shps[1:]:
        logger.info('Reading: {}'.format(s))
        shp2 = gpd.read_file(s)
        if len(shp2) > 1:
            shp2 = dissolve_gdf(shp2)
        logger.info('Finding intersection...')
        shp = gpd.overlay(shp, shp2)

    return shp


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_shps', type=os.path.abspath, nargs='*',
                        help='Vector files to find the intersection of.')
    parser.add_argument('-o', '--out_intersection', type=os.path.abspath,
                        help='Path to write intersection out to.')

    args = parser.parse_args()

    intersection = intersect_aois(args.input_shps)

    logger.info('Writing intersection to: {}'.format(args.out_intersection))
    intersection.to_file(args.out_intersection)
