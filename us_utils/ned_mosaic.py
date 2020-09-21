# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 17:04:46 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import subprocess
import platform

import geopandas as gpd

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

tiles_path_win = r'E:\disbr007\general\geocell\us_one_degree_geocells_named.shp'
tiles_path_linux = r'/mnt/pgc/data/scratch/jeff/general/geocell/us_one_degree_geocells_named.shp'


def main(aoi_path, out_mosaic, local_tiles_dir, tile_index=None):
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = proc.communicate()
        logger.info('Output: {}'.format(output))
        # if error:
            # logger.info('Err: {}'.format(error))

    # Parameters
    tile_id = 'name'

    ftp_dir = r'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF'
    # tiles_dir = r'V:\pgc\data\elev\dem\ned\tiles\NED_13\grid'
    if tile_index:
        tiles_path = tile_index
    else:
        if platform.system() == 'Windows':
            tiles_path = tiles_path_win
        elif platform.system() == 'Linux':
            tiles_path = tiles_path_linux
        else:
            logger.error('Unknown platform: {}'.format(platform.system()))

    logger.info('Reading in tile index...')
    tiles = gpd.read_file(tiles_path)
    logger.debug('Tiles loaded in index: {:,}'.format(len(tiles)))
    aoi = gpd.read_file(aoi_path)
    logger.debug('Features found in AOI input: {:,}'.format(len(aoi)))
    if aoi.geometry.type[0] == 'Point':
        aoi.geometry = aoi.geometry.buffer(0.5)

    # Select AOI relevant tiles:
    logger.info('Identifying necessary tiles...')
    if aoi.crs != tiles.crs:
        aoi = aoi.to_crs(tiles.crs)
    logger.debug('AOI CRS: {}'.format(aoi.crs))
    logger.debug('Tiles CRS: {}'.format(tiles.crs))

    selected_tiles = gpd.sjoin(aoi, tiles)
    logger.debug('Tiles selected: {}'.format(len(selected_tiles)))

    # Overlay results in duplicates, so remove
    selected_tiles = selected_tiles.drop_duplicates(subset=['name'])
    logger.info('Total number of tiles needed for selection: {}'.format(len(selected_tiles)))

    # Create local path
    selected_tiles['full_path'] = selected_tiles['name'].apply(lambda x: os.path.join(local_tiles_dir,
                                                                                      'USGS_1_{}.tif'.format(x)))
    # Create https address to download from
    selected_tiles['ftp_path'] = selected_tiles['name'].apply(lambda x: '{}/{}/USGS_1_{}.tif'.format(ftp_dir,
                                                                                                     x,x))
    # Create BOOL field that identifies if tile is already present in local directory
    selected_tiles['downloaded'] = selected_tiles['full_path'].apply(lambda x: os.path.exists(x))

    logger.info('Tiles already downloaded: {}'.format(len(selected_tiles[selected_tiles['downloaded']==True])))
    logger.info('Tiles to be downloaded: {}'.format(len(selected_tiles[selected_tiles['downloaded']==False])))

    # Full paths included provided local tiles download directory as strings
    logger.debug('DEM paths for mosaicking:\n{}'.format('\n'.join(list(selected_tiles['full_path']))))
    dems_paths = ' '.join(list(selected_tiles['full_path']))
    # dems_dl = ' '.join([x for x in list(selected_tiles['full_path']) if not os.path.exists(x)])

    # Write list of files to download to text file, use that with wget -i command
    if len(selected_tiles[selected_tiles['downloaded']==False]) != 0:
        logger.info('Downloading NED tiles...')
        text_urls = os.path.join(local_tiles_dir, 'ned_tile_urls_tmp.txt')
        with open(text_urls, 'w') as ot:
            # Write any non-downloaded tile urls to a text
            for dl_url in list(selected_tiles[selected_tiles['downloaded']==False]['ftp_path']):
                ot.write(dl_url)
                ot.write('\n')

        command = "wget -i {} -P {}".format(text_urls, local_tiles_dir)
        print(command)
        run_subprocess(command)

        # Delete text file of tiles
        # os.remove(text_urls)

    logger.info('Mosaicking NED tiles...')
    command = 'gdalbuildvrt {} {}'.format(out_mosaic, dems_paths)

    run_subprocess(command)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('aoi_path', type=os.path.abspath,
                                     help='Path to AOI to use to select tiles.')
    parser.add_argument('out_mosaic', type=os.path.abspath,
                        help='Path to write mosaic to, .vrt format recommended.')
    parser.add_argument('local_tiles_dir', type=os.path.abspath,
                        help='Path to download tiles to.')
    parser.add_argument('--tile_index', type=os.path.abspath,
                        help='Path to shapefile of ned tile index.')

    args = parser.parse_args()

    aoi_path = args.aoi_path
    out_mosaic = args.out_mosaic
    local_tiles_dir = args.local_tiles_dir
    tile_index = args.tile_index

    main(aoi_path, out_mosaic, local_tiles_dir, tile_index)
