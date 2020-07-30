# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 17:04:46 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import platform
import subprocess

import geopandas as gpd

from misc_utils.logging_utils import create_logger, LOGGING_CONFIG


# logger = create_logger(os.path.basename(__file__), 'sh')


def main(aoi_path, out_mosaic, dryrun=False, verbose=False):
    
    # Logging setup
    if verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'

    logging.config.dictConfig(LOGGING_CONFIG(handler_level))
    logger = logging.getLogger(__name__)
    
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = proc.communicate()
        logger.info('Output: {}'.format(output))
        logger.info('Err: {}'.format(error))

    # Parameters
    if platform.system() == 'Windows':
        tandemx_dir = r'V:\pgc\data\elev\dem\tandem-x\90m'
    elif platform.system() == 'Linux':
        tandemx_dir = r'/mnt/pgc/data/elev/dem/tandem-x/90m'

    tiles_dir = os.path.join(tandemx_dir, '1deg_cells')
    tiles_idx = os.path.join(tandemx_dir, 'index', 'tandem-x_90m.shp')

    logger.info('Loading tiles index...')
    ti = gpd.read_file(tiles_idx)
    logger.info('Loading AOI...')
    aoi = gpd.read_file(aoi_path)
    if aoi.crs != ti.crs:
        aoi = aoi.to_crs(ti.crs)
    logger.info('Locating intersecting tiles...')
    selected_tiles = gpd.overlay(aoi, ti)
    logger.info('Number of tiles located: {}'.format(len(selected_tiles)))

    # ti['fullpath'] = ti['location'].apply(lambda x: os.path.join(tiles_dir, x))
    tile_paths = ' '.join([os.path.join(tiles_dir, x) for x in list(selected_tiles['location'])])
    # tile_paths_str = 
    logger.info('Mosaicking TanDEM-X tiles...')
    # TODO: FIX no data values
    command = 'gdalbuildvrt {} {} -vrtnodata -32767'.format(out_mosaic, tile_paths)
    logger.debug('Command:\n{}'.format(command))

    if not dryrun:
        run_subprocess(command)
        logger.info('Mosaic complete.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('aoi_path', type=os.path.abspath,
                                     help='Path to AOI to use to select tiles.')
    parser.add_argument('out_mosaic', type=os.path.abspath,
                        help='Path to write mosaic to, .vrt format recommended.')
    parser.add_argument('-v', '--verbose', action='store_true',
                         help='Set logging level to DEBUG')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print mosaic command without running.')

    args = parser.parse_args()

    aoi_path = args.aoi_path
    out_mosaic = args.out_mosaic
    verbose = args.verbose
    dryrun = args.dryrun

    main(aoi_path, out_mosaic, dryrun=dryrun, verbose=verbose)

