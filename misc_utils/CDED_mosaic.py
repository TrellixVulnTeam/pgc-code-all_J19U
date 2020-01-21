# -*- coding: utf-8 -*-
"""
Created on Thu May  9 11:04:23 2019

@author: disbr007
CDED Mosaicker based on AOI
"""

import geopandas as gpd
import os, zipfile, tqdm, subprocess

from osgeo import gdal

from logging_utils import create_logger


# Inputs
selected_res = 'cded_50k'
driver = 'ESRI_Shapefile'
aoi_path = r'E:\disbr007\general\elevation\cded\50k_mosaics\illa_sel.shp'
project_path = os.path.dirname(aoi_path)

# Set up logging
logger = create_logger('CDED_mosaic.py', 'sh')

## Choose 50k or 250k
logger.debug('Using selected resolution: {}'.format(selected_res))
cded_50k_index_path = r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc50k_2.shp'
cded_250k_index_path = r'V:\pgc\data\elev\dem\cded\index\decoupage_snrc250k_2.shp'

if selected_res == 'cded_50k':
    index_path = cded_50k_index_path
    tiles_path = r'V:\pgc\data\elev\dem\cded\50k_dem'
elif selected_res == 'cded_250k':
    index_path = cded_250k_index_path
    tiles_path = r'V:\pgc\data\elev\dem\cded\250k_dem'
else:
    print('Index footprint not found')
logger.debug('Using tiles located at: {}'.format(tiles_path))

# load relevant footprint
index = gpd.read_file(index_path, driver=driver)
index_crs = index.crs

# Load index selection
# selected_tiles = gpd.read_file(aoi_path)

## Select AOI relevant tiles from index footprint
aoi = gpd.read_file(aoi_path, driver=driver)
aoi_proj = aoi.copy()
aoi_proj = aoi_proj.to_crs(index_crs)
# selected_tiles = gpd.sjoin(aoi_proj, index, how='left', op='intersects')
selected_tiles = gpd.overlay(aoi_proj, index)

# For some reason the sjoin is selecting each tile multiple times -- this gets a list of unique tile names for extracting
# selected_tile_names = selected_tiles.IDENTIF.unique() 
selected_tile_names = [x.lower() for x in selected_tile_names] # file paths to tiles are lowercase

## Unzip relevant tiles to local location
# Create local directory for tiles
local_tiles_path = os.path.join(project_path, 'CDED_tiles')
if os.path.exists(local_tiles_path):
    pass
else:
    os.makedirs(local_tiles_path)

# Loop each tile name, extract tile locally
print('Extracting...')
for tile_name in tqdm.tqdm(selected_tile_names):
    parent_dir = tile_name[:3]
    tile_path = os.path.join(tiles_path, parent_dir, '{}.zip'.format(tile_name))
    if os.path.exists(tile_path):
        zip_ref = zipfile.ZipFile(tile_path, 'r')
        tile_dir_extract = zip_ref.extractall(local_tiles_path)
        zip_ref.close()
    else:
        print('File not found: {}\nSkipping...'.format(tile_name))
    
    
## Mosaic relevant tiles
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    print('Output: {}'.format(output))
    print('Err: {}'.format(error))


dems_path = os.path.join(local_tiles_path,r'*.dem')
command = 'gdalbuildvrt {} {}'.format(out_mosaic, dems_path)

run_subprocess(command)

# dems = os.listdir(local_tiles_path)
# dems = [d for d in dems if d.endswith('.dem')]
# dems = [os.path.join(local_tiles_path, d) for d in dems]
# ds = gdal.BuildVRT(r'E:\disbr007\general\elevation\cded\50k_mosaics\illa\illa_cded_mosaic.tif', dems))
# ds = None
