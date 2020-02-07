# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 17:04:46 2020

@author: disbr007
"""

import argparse
import os
import subprocess

import geopandas as gpd

from logging_utils import create_logger


# # INPUTS
# aoi_path = r'E:\disbr007\UserServicesRequests\Projects\akhan\aoi_pts.shp'
# out_mosaic = r'C:\temp\ned_mosaic.vrt'
# local_tiles_dir = r'C:\temp'

logger = create_logger(os.path.basename(__file__), 'sh')


def main(aoi_path, out_mosaic, local_tiles_dir):
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = proc.communicate()
        print('Output: {}'.format(output))
        print('Err: {}'.format(error))

    # Parameters
    tile_id = 'name'

    ftp_dir = r'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF'
    # tiles_dir = r'V:\pgc\data\elev\dem\ned\tiles\NED_13\grid'
    tiles_path = r'E:\disbr007\general\geocell\us_one_degree_geocells_named.shp'

    tiles = gpd.read_file(tiles_path)
    aoi = gpd.read_file(aoi_path)
    if aoi.geometry.type[0] == 'Point':
        aoi.geometry = aoi.geometry.buffer(0.5)

    # Select AOI relevant tiles:
    if aoi.crs != tiles.crs:
        aoi = aoi.to_crs(tiles.crs)
        
    selected_tiles = gpd.overlay(aoi, tiles)

    selected_tiles['full_path'] = selected_tiles['name'].apply(lambda x: os.path.join(local_tiles_dir,
                                                                                      'USGS_1_{}.tif'.format(x)))
    selected_tiles['ftp_path'] = selected_tiles['name'].apply(lambda x: '{}/{}/USGS_1_{}.tif'.format(ftp_dir,
                                                                                                     x,x))
    dems_https = ' '.join(list(selected_tiles['ftp_path']))
    dems_paths = ' '.join(list(selected_tiles['full_path']))
    dems_dl = ' '.join([x for x in list(selected_tiles['full_path']) if not os.path.exists(x)])

    if dems_dl:
        logger.info('Downloading NED tiles...')
        command = "wget {} -P {}".format(dems_https, local_tiles_dir)
        run_subprocess(command)

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

    args = parser.parse_args()

    aoi_path = args.aoi_path
    out_mosaic = args.out_mosaic
    local_tiles_dir = args.local_tiles_dir

    main(aoi_path, out_mosaic, local_tiles_dir)
