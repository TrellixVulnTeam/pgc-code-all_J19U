# -*- coding: utf-8 -*-
"""
Created on Thu May  9 11:04:23 2019

@author: disbr007
ArcticDEM Mosaic Tile Mosaicker based on AOI
"""

import argparse
import numpy as np
import os
import platform
import subprocess
import tarfile

import geopandas as gpd
from osgeo import gdal
from tqdm import tqdm

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'DEBUG')


# Inputs
# aoi_path = r'V:\pgc\data\scratch\jeff\ms\2020may12\footprints\aoi1_dem_fps_danco.shp'
# # Optional (have default)
# tiles_dir = r'V:\pgc\data\scratch\jeff\elev\arcticdem\tiles\ind_tiles' # directory of tiles / directory to download tiles to
# out_mosaic = r'V:\pgc\data\scratch\jeff\elev\arcticdem\tiles\mosaics\2020may12_aoi1_scene.tif'

# # Params
# tiles_index_path = r'E:\disbr007\arctic_dem\ArcticDEM_Tile_Index_Rel7\ArcticDEM_Tile_Index_Rel7.shp'
# tile_name = 'name'
# fileurl = 'fileurl'
# # Created
# dem_path = 'dem_path'
# dem_exist = 'dem_exist'
# gz_path = 'gz_path'
# gz_exist = 'gz_exist'
# to_dl = 'to_dl'
# to_unzip = 'to_unzip'


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    logger.info('Output: {}'.format(output))
    if error:
        logger.info('Err: {}'.format(error))
        logger.info('Command: {}'.format(command))


def locate_tiles(aoi_path, tiles_path, tile_name='name'):
    # Read AOI
    aoi = gpd.read_file(aoi_path)
    # Read tiles index
    tiles_index = gpd.read_file(tiles_path)
    
    # Locate tiles
    aoi_tiles = gpd.overlay(tiles_index, aoi)
    logger.info('Tiles identified over AOI: {}'.format(len(aoi_tiles)))
    logger.debug('\n'.join(list(aoi_tiles[tile_name])))
    
    return aoi_tiles


def check_exist(gdf, path_field, exist_field):
    gdf[exist_field] = gdf.apply(lambda x: os.path.exists(x[path_field]))
    

def download_tiles(download_urls, download_dir):
    # Download urls
    logger.info('Downloading tarfiles: {}'.format(len(download_urls)))
    for url in tqdm(download_urls):
        # Download
        logger.debug('wget-ting: {}'.format(url))
        log_file = os.path.join(tiles_dir, 'wget_log.txt')
        cmd = r"""wget --directory-prefix {} -o {} {}""".format(download_dir, log_file, url)
        run_subprocess(cmd)



def unzip_tarfiles(gzs, tiles_dir):
    # Unzip tarfiles
    logger.info('Unzipping tarfiles: {}'.format(len(gzs)))
    for gz in tqdm(gzs):
        # Unzip to dems_dir
        # dst_dem = get_dem_dst(dems_dir, gz)
        # dem_subdir = os.path.join(dems_dir, os.path.splitext(os.path.basename(dst_dem))[0])
        # if not os.path.exists(dem_subdir):
        #     os.makedirs(dem_subdir)
        # if not os.path.exists(dst_dem):
        logger.debug('Unzipping: {}'.format(gz))
        with tarfile.open(gz, 'r:gz') as tar:
            tar.extractall(tiles_dir)


def mosaic_tiles(tile_paths, out_mosaic):
    logger.info('Mosaicing tiles...')
    if out_mosaic.endswith('tif'):
        logger.debug('Extension is "tif", creating in-memory VRT first...')
        vrt = r'/vsimem/cded_mosaic_temp.vrt'
        gdal.BuildVRT(vrt, tile_paths)
        logger.debug('Copying VRT to GeoTiff...')
        # translate_options = gdal.TranslateOptions(format='GTiff')
        gdal.Translate(out_mosaic, vrt, options=gdal.TranslateOptions(format='GTiff'))
    # run_subprocess(command)
    else:
        gdal.BuildVRT(out_mosaic, tile_paths)
    logger.info('Mosaic created at: {}'.format(out_mosaic))
    

def arcticdem_mosaic(aoi_path, out_mosaic=out_mosaic, 
                     tiles_dir=None, tiles_index_path=None,
                     tile_name='tile_name', gz_path='gz_path', dem_path='dem_path',
                     gz_exist='gz_exist', dem_exist='dem_exist',
                     to_dl='to_dl', to_unzip='to_unzip', fileurl='fileurl'):
    
    # If tiles index not provided, use defaults
    if tiles_index_path is None:
        if platform.system() == 'Windows':
            tiles_index_path = r'V:\pgc\data\scratch\jeff\elev\arcticdem\ArcticDEM_Tile_Index_Rel7\ArcticDEM_Tile_Index_Rel7.shp'
        elif platform.system() == 'Linux':
            tiles_index_path = r'/mnt/pgc/data/scratch/jeff/elev/arcticdem/ArcticDEM_Tile_Index_Rel7/ArcticDEM_Tile_Index_Rel7.shp'
    if tiles_dir is None:
        if platform.system() == 'Windows':
            tiles_dir = r'V:\pgc\data\scratch\jeff\elev\arcticdem\tiles\ind_tiles'
        elif platform.system() == 'Linux':
            tiles_dir = r'/mnt/pgc/data/scratch/jeff/elev/arcticdem/tiles/ind_tiles'    
    
    # Identify tiles that overlap AOI
    aoi_tiles = locate_tiles(aoi_path, tiles_path=tiles_index_path)
    
    # Create path where tar.gz would be if it existed
    aoi_tiles[gz_path] = aoi_tiles.apply(lambda x: os.path.join(tiles_dir, '{}.tar.gz'.format(x[tile_name])), axis=1)
    # Create path where DEM would be if it existed
    aoi_tiles[dem_path] = aoi_tiles.apply(lambda x: os.path.join(tiles_dir, '{}_reg_dem.tif'.format(x[tile_name])), axis=1)
    
    # Check for existence of tar.gz's and DEMs locally
    check_exist(aoi_tiles, gz_path, gz_exist)
    check_exist(aoi_tiles, dem_path, dem_exist)
    
    # Create list where tar.gz and DEM do not exist -> to download
    aoi_tiles[to_dl] = ~aoi_tiles[gz_exist] & ~aoi_tiles[dem_exist]
    download_urls = list(aoi_tiles[aoi_tiles[to_dl]][fileurl])
    
    # Download any tiles that do not exist locally
    download_tiles(download_urls=download_urls, download_dir=tiles_dir)
    
    # Update list of existing gz's
    check_exist(aoi_tiles, gz_path, gz_exist)
    
    # Unzip
    aoi_tiles[to_unzip] = aoi_tiles[gz_exist] & ~aoi_tiles[dem_exist]
    gzs = list(aoi_tiles[aoi_tiles[to_unzip]][gz_path])
    unzip_tarfiles(gzs, tiles_dir)
    
    # Mosaic
    # Check if all dems now exist
    check_exist(aoi_tiles, dem_path, dem_exist)
    
    if not np.all(aoi_tiles[dem_exist]):
        logger.error('Missing DEM tiles:\n{}'.format('\n'.join(list(aoi_tiles[~aoi_tiles[dem_exist]][tile_name]))))
        raise Exception
        
    tile_paths = list(aoi_tiles[dem_path])
    
    # Mosaic    
    mosaic_tiles(tile_paths=tile_paths, out_mosaic=out_mosaic)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--aoi', type=os.path.abspath,
                        help='Path to AOI.')
    parser.add_argument('--tiles_dir', type=os.path.abspath,
                        help="""Path to local directory where tiles are stored. New tiles will
                                be downloaded here.""")
    parser.add_argument('-o', '--out_mosaic', type=os.path.abspath,
                        help='Path to write mosaic to.')
    
    args = parser.parse_args()
    
    aoi_path = args.aoi
    out_mosaic = args.out_mosaic
    tiles_dir = args.tiles_dir
    
    arcticdem_mosaic(aoi_path=aoi_path, out_mosaic=out_mosaic, tiles_dir=tiles_dir)
