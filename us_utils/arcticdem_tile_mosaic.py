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
import sys

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
if platform.system() == 'Windows':
    tiles_local = r'V:\pgc\data\elev\dem\setsm\ArcticDEM\mosaic\v3.1\2m_lsf'
elif platform.system() == 'Linux':
    tiles_local = r'/mnt/pgc/data/elev/dem/setsm/ArcticDEM/mosaic/v3.1/2m_lsf'
dem_end = '_reg_dem.tif'


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

    # Confirm CRS is same or reproject
    if aoi.crs != tiles_index.crs:
        logger.debug('Reprojecting AOI to match tiles index CRS: {} -> {}'.format(aoi.crs, tiles_index.crs))
        aoi = aoi.to_crs(tiles_index.crs)
    # Locate tiles
    aoi_tiles = gpd.overlay(tiles_index, aoi)
    logger.info('Tiles identified over AOI: {}'.format(len(aoi_tiles)))
    if len(aoi_tiles) == 0:
        logger.warning('No tiles identified over AOI')
        logger.warning('AOI crs: {}'.format(aoi.crs))
        logger.warning('Tiles CRS: {}'.format(tiles_index.crs))
        sys.exit()
    logger.debug('\n' + '\n'.join(list(sorted(aoi_tiles[tile_name]))))
    
    return aoi_tiles


def check_exist(gdf, path_field, exist_field):
    gdf[exist_field] = gdf.apply(lambda x: os.path.exists(x[path_field]), axis=1)
    

def download_tiles(download_urls, download_dir):
    # Download urls
    logger.info('Downloading tarfiles: {}'.format(len(download_urls)))
    for url in tqdm(download_urls):
        # Download
        logger.debug('wget-ting: {}'.format(url))
        log_file = os.path.join(download_dir, 'wget_log.txt')
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
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tar, tiles_dir)


def mosaic_tiles(tile_paths, out_mosaic):
    logger.info('Mosaicing tiles...')
    # TODO: Is this faster than creating a tif directly...?
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
    

def arcticdem_mosaic(aoi_path, out_mosaic, 
                     tiles_dir=None, tiles_index_path=None, download=False,
                     tile_name='name', gz_path='gz_path', dem_path='dem_path',
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

    if download:
        logger.info('Downloading tiles...')
        # Create path where tar.gz would be if it existed
        aoi_tiles[gz_path] = aoi_tiles.apply(lambda x: os.path.join(tiles_dir, '{}.tar.gz'.format(x[tile_name])), axis=1)
        # Create path where DEM would be if it existed
        aoi_tiles[dem_path] = aoi_tiles.apply(lambda x: os.path.join(tiles_dir, '{}_reg_dem.tif'.format(x[tile_name])), axis=1)

        # Check for existence of tar.gz's and DEMs locally
        check_exist(aoi_tiles, gz_path, gz_exist)
        logger.info('Tarfiles found locally: {}'.format(len(aoi_tiles[aoi_tiles[gz_exist]==True])))
        check_exist(aoi_tiles, dem_path, dem_exist)
        logger.info('DEMs found locally: {}'.format(len(aoi_tiles[aoi_tiles[dem_exist]==True])))

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
    else:
        logger.debug('Using local tiles at: {}'.format(tiles_local))
        aoi_tiles[dem_path] = aoi_tiles.apply(lambda x: os.path.join(tiles_local, x['tile'],
                                                                     '{}{}'.format(x['name'], dem_end)),
                                              axis=1)
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
    parser.add_argument('--download', action='store_true',
                        help='Download tiles rather than using local copies.')
    parser.add_argument('-o', '--out_mosaic', type=os.path.abspath,
                        help='Path to write mosaic to.')
    
    args = parser.parse_args()
    
    aoi_path = args.aoi
    out_mosaic = args.out_mosaic
    tiles_dir = args.tiles_dir
    download = args.download
    
    arcticdem_mosaic(aoi_path=aoi_path, out_mosaic=out_mosaic, tiles_dir=None, download=download)
