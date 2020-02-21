# -*- coding: utf-8 -*-
"""
Created on Thu May  9 11:04:23 2019

@author: disbr007
CDED Mosaicker based on AOI
"""

import argparse
import logging.config
import os
import platform
import subprocess
import zipfile

import geopandas as gpd
from osgeo import gdal
import tqdm

from misc_utils.logging_utils import LOGGING_CONFIG


handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    logger.info('Output: {}'.format(output))
    if error:
        logger.info('Err: {}'.format(error))


def main(args):

    # Parse arguments
    aoi_path = args.aoi
    resolution = args.resolution
    out_mosaic = args.out_mosaic
    local_tiles_path = args.local_tiles_path

    # Determine operating system
    system = platform.system()
    if system == 'Windows':
        params = {'def_local_tiles_path': r'E:\disbr007\general\elevation\cded\50k_mosaics\CDED_tiles',
                  'cded_50_idx': r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc50k_2.shp',
                  'cded_250_idx': r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc250k_2.shp',
                  'cded_50_tiles': r'V:\pgc\data\elev\dem\cded\50k_dem',
                  'cded_250_tiles': r'V:\pgc\data\elev\dem\cded\250k_dem'}
    elif system == 'Linux':
        params = {'def_local_tiles_path': r'/mnt/pgc/data/scratch/jeff/elev/cded/tiles',
                  'cded_50_idx': r'/mnt/pgc/data/elev/dem/cded/index/decoupage_snrc50k_2.shp',
                  'cded_250_idx': r'/mnt/pgc/data/elev/dem/cded/index/decoupage_snrc50k_2.shp',
                  'cded_50_tiles': r'/mnt/pgc/data/elev/dem/cded/50k_dem/',
                  'cded_250_tiles': r'/mnt/pgc/data/elev/dem/cded/250k_dem/'}

    if not local_tiles_path:
        # local_tiles_path = r'E:\disbr007\general\elevation\cded\50k_mosaics\CDED_tiles'
        local_tiles_path = params['def_local_tiles_path']
        logger.debug('No local tiles path specified, using default:\n{}'.format(local_tiles_path))
    if not os.path.exists(local_tiles_path):
        os.makedirs(local_tiles_path)


    ## Choose 50k or 250k
    logger.debug('Using selected resolution: {}'.format(resolution))
    # cded_50k_index_path = params['cded_50_idx']
    # cded_250k_index_path = params['cded_250_idx']
    # cded_50k_index_path = r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc50k_2.shp'
    # cded_250k_index_path = r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc250k_2.shp'
    
    if resolution == 50:
        # index_path = cded_50k_index_path
        # tiles_path = r'V:\pgc\data\elev\dem\cded\50k_dem'
        index_path = params['cded_50_idx']
        tiles_path = params['cded_50_tiles']
    elif resolution == 250:
        # index_path = cded_250k_index_path
        # tiles_path = r'V:\pgc\data\elev\dem\cded\250k_dem')
        index_path = params['cded_250_idx']
        tiles_path = params['cded_250_tiles']

    else:
        logger.warning('Index footprint not found')
    logger.debug('Using tiles located at: {}'.format(tiles_path))
    
    # Load relevant tikes index
    index = gpd.read_file(index_path)
    
    
    ## Select AOI relevant tiles from index footprint
    aoi = gpd.read_file(aoi_path)
    logger.info('AOI:\n{}'.format(aoi.head()))
    if aoi.crs != index.crs:
        aoi = aoi.to_crs(index.crs)
    # selected_tiles = gpd.sjoin(aoi, index, how='left', op='intersects')
    selected_tiles = gpd.overlay(aoi, index)
    
    # For some reason the overlay is selecting each tile multiple times -- 
    # this gets a list of unique tile names for extracting
    selected_tile_names = selected_tiles.IDENTIF.unique()
    selected_tile_names = [x.lower() for x in selected_tile_names] # file paths to tiles are lowercase


    ## Unzip relevant tiles to local location
    # Loop each tile name, extract tile locally
    logger.info('Extracting tiles locally...')
    for tile_name in tqdm.tqdm(selected_tile_names):
        parent_dir = tile_name[:3]
        tile_path = os.path.join(tiles_path, parent_dir, '{}.zip'.format(tile_name))
        if os.path.exists(tile_path):
            zip_ref = zipfile.ZipFile(tile_path, 'r')
            tile_dir_extract = zip_ref.extractall(local_tiles_path)
            zip_ref.close()
        else:
            logger.warning('File not found: {}\nSkipping...'.format(tile_name))
        
        
    ## Mosaic relevant tiles
    # Get DEMs
    # Select only tile paths from initial selection above
    dems_paths = [os.path.join(local_tiles_path, x) for x in os.listdir(local_tiles_path) if x.endswith('dem')]
    dems_paths = [x for x in dems_paths if os.path.basename(x).startswith(tuple(selected_tile_names))]
    dems_paths = ' '.join(dems_paths)
    
    command = 'gdalbuildvrt {} {}'.format(out_mosaic, dems_paths)
    
    logger.info('Mosaicking tiles...')
    run_subprocess(command)
    logger.info('Mosaic created at: {}'.format(out_mosaic))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('aoi', type=os.path.abspath,
                        help='Path to AOI shapefile.')
    parser.add_argument('resolution', type=int,
                        help='Resolution of CDED tiles to use: "50" or "250"')
    parser.add_argument('out_mosaic', type=os.path.abspath,
                        help="""Path to write mosaic to. A file extension of .vrt 
                                will write more quickly, but .tif is also acceptable""")
    parser.add_argument('--local_tiles_path', type=os.path.abspath,
                        help='Path to unzip cded tiles to.')
    
    args = parser.parse_args()
    
    main(args)
                        