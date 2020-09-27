import argparse
import os

import geopandas as gpd

from misc_utils.gpd_utils import merge_gdfs
from misc_utils.logging_utils import create_logger


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--shapefiles', nargs='+', type=os.path.abspath,
                        help='Paths to shapefile to merge.')
    parser.add_argument('-o', '--out_shapefile', type=os.path.abspath,
                        help='Path to write merged shapefile to.')
    parser.add_argument('-r', '--remove_dup', type=str,
                        help='Remove duplicates based on field name provided.')
    parser.add_argument('-v', '--verbose', action='store_true')

    # TODO: add ignore fields, or finding same fields and dropping others

    args = parser.parse_args()

    if args.verbose:
        log_lvl = 'DEBUG'
    else:
        log_lvl = 'INFO'
    logger = create_logger(__name__, 'sh', log_lvl)

    logger.info('Reading in shapefiles...')
    gdfs = []
    for shp in args.shapefiles:
        gdf = gpd.read_file(shp)
        gdf['name'] = os.path.splitext(os.path.basename(shp))[0]
        gdfs.append(gdf)
    for i, g in enumerate(gdfs):
        logger.debug('Shapefile {}: {} features'.format(i, len(g)))
    merged = merge_gdfs(gdfs)
    logger.debug('Merged shapefile length: {}'.format(len(merged)))

    if args.remove_dup:
        if args.remove_dup not in list(merged):
            logger.error('Field for removing DUPs not in shapefile: {}'.format(args.remove_dup))
        logger.info('Removing dupicates based on: {}'.format(args.remove_dup))
        logger.debug('Merged shapefile length after removing DUPs: {}'.format(len(merged)))
        merged = merged.drop_duplicates(subset=args.remove_dup)

    logger.info('Writing to {}'.format(args.out_shapefile))
    merged.to_file(args.out_shapefile)
