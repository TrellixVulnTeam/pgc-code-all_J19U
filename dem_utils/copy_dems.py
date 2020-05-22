# -*- coding: utf-8 -*-
"""
Created on Fri May  8 13:13:23 2020

@author: disbr007
"""
import argparse
import os
import shutil

import pandas as pd
import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger
from dem_utils.dem_utils import get_filepath_field, get_dem_path
# from dem_utils import get_filepath_field, get_dem_path

logger = create_logger(__name__, 'sh', 'INFO')

#%% Load Footprint - Check existence
def get_footprint_dems(footprint_path, filepath=get_filepath_field(),
                       dem_name='dem_name', dem_path_fld='dem_path',
                       dem_exist_fld='dem_exist'):
    if isinstance(footprint_path, list):
        # List of paths
        fp = pd.DataFrame({dem_path_fld: footprint_path})
    else:
        if isinstance(footprint_path, str):
            # Paths in text file
            if os.path.splitext(footprint_path) == '.txt':
                with open(footprint_path, 'r') as src:
                    content = src.readlines()
                fp = pd.DataFrame({dem_path_fld: content})
        # Vector file of footprints with path field
        else:
            if isinstance(footprint_path, gpd.GeoDataFrame):
                fp = footprint_path
            else:
                # Load footprint
                logger.info('Loading DEM footprint...')
                fp = gpd.read_file(footprint_path)
                fp[dem_path_fld] = fp.apply(lambda x: get_dem_path(x[filepath], x[dem_name]), axis=1)
            num_fps = len(fp)
            logger.info('Records found: {}'.format(num_fps))

    fp[dem_exist_fld] = fp.apply(lambda x: os.path.exists(x[dem_path_fld]), axis=1)

    dem_paths = list(fp[fp[dem_exist_fld] == True][dem_path_fld])
    num_exist_fps = len(fp)
    if num_exist_fps != num_fps:
        logger.warning('Filepaths could not be found for {} records, skipping...'.format(num_fps - num_exist_fps))

    return dem_paths


#%% Create copy list
def create_copy_list(dem_paths, dest_parent_dir, meta_file_sfx, flat=False):
    copy_list = []
    for dem in dem_paths:
        dem_dirname = os.path.basename(os.path.dirname(dem))
        if not flat:
            dst_dir = os.path.join(dest_parent_dir, dem_dirname)
        else:
            dst_dir = dest_parent_dir
        meta_files = []
        for sfx in meta_file_sfx:
            mf = dem.replace('dem.tif', sfx)
            if os.path.exists(mf):
                meta_files.append(mf)
            else:
                logger.debug('Missing metadata file: {}'.format(mf))
        if not os.path.exists(os.path.join(dst_dir, os.path.basename(dem))):
            copy_list.append((dem, dst_dir))
        copy_list.extend([(mf, dst_dir) for mf in meta_files
                          if not os.path.exists(os.path.join(dst_dir, os.path.basename(mf)))])

    return copy_list


#%% Copy
def copy_dems(footprint_path, output_directory, 
              dems_only=False, skip_ortho=False,
              flat=False, dryrun=False):
    if dems_only:
        logger.debug('Copying DEMs only.')
        meta_file_sfx = []
    else:
        meta_file_sfx = ['dem.log',
                          # 'ortho_browse.tif',
                          'dem.tif.aux.xml',
                          'density.txt',
                          'mdf.txt',
                          'reg.txt',
                          'dem_browse.tif',
                          'meta.txt',
                          'ortho.tif',
                          'matchtag.tif']
        if skip_ortho:
            logger.debug('Skipping ortho files.')
            meta_file_sfx.remove('ortho.tif')

    dem_paths = get_footprint_dems(footprint_path)
    copy_list = create_copy_list(dem_paths, output_directory, meta_file_sfx, flat=flat)

    dem_src_list = [pair[0] for pair in copy_list if pair[0].endswith('dem.tif')]
    dem_dst_list = [os.path.join(pair[1], os.path.basename(pair[0])) for pair in copy_list if pair[0].endswith('dem.tif')]

    logger.info('Located DEMs to copy: {}'.format(len(dem_src_list)))

    total_src_dems = len(dem_src_list)
    remaining_dems = total_src_dems
    pbar = tqdm(copy_list, desc='Remaining DEMs: {}'.format(remaining_dems))
    for src, dst in pbar:
        try:
            if not dryrun:
                pbar.write('Copying: {}'.format(os.path.basename(src)))
                if not os.path.exists(dst):
                    os.makedirs(dst)
                dst_file = os.path.join(dst, os.path.basename(src))
                if not os.path.exists(dst_file):
                    shutil.copy2(src, dst)
                else:
                    pbar.write('Skipping (exists): {}'.format(dst_file))
            # else:
            #     pbar.write('[DRYRUN] Copying: {}'.format(src))
        except Exception as e:
            logger.warning('Failed to copy: {}'.format(src))
            logger.error(e)
        finally:
            if src.endswith('dem.tif'):
                remaining_dems -= 1
                pbar.set_description('Remaining DEMs: {}'.format(remaining_dems))
    
    copied_dems = [d for d in dem_dst_list if os.path.exists(d)]
    num_copied_dems = len(copied_dems)
    logger.info('Successfully copied DEMs: {}'.format(num_copied_dems))
    
    if (total_src_dems != num_copied_dems) and not dryrun:
        logger.warning('Missing DEMs in destination: {}'.format(total_src_dems - num_copied_dems))
        missing_dems = [d for d in dem_dst_list if d not in copied_dems]
        logger.debug('Missing DEMs:\n{}'.format('\n'.join(missing_dems)))


#%%
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_footprint_path', type=os.path.abspath,
                        help='Path to footprint containing DEM paths.')
    parser.add_argument('-o', '--output_directory', type=os.path.abspath,
                        help='Path to directory to copy to.')
    parser.add_argument('-do', '--dems_only', action='store_true',
                        help='Use to only copy dem.tif files.')
    parser.add_argument('-so', '--skip_ortho', action='store_true',
                        help='Use to skip ortho files, but copy all other meta files.')
    parser.add_argument('-f', '--flat', action='store_true',
                        help='Use to not create DEM subdirectories, just copy to destination directory.')
    parser.add_argument('-dr', '--dryrun', action='store_true',
                        help='Use to check for DEMs existence but do not copy.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logger to DEBUG.')
    
    args = parser.parse_args()
    
    footprint_path = args.input_footprint_path
    output_directory = args.output_directory
    dems_only = args.dems_only
    skip_ortho = args.skip_ortho
    flat = args.flat
    dryrun = args.dryrun
    verbose = args.verbose
    
    # if verbose:
    #     log_lvl = 'DEBUG'
    # else:
        # log_lvl = 'INFO'


    copy_dems(footprint_path, output_directory,
              dems_only=dems_only, skip_ortho=skip_ortho,
              flat=flat, dryrun=dryrun)



# # Inputs
# footprint_path = r'V:\pgc\data\scratch\jeff\ms\2020apr30\footprints\aoi1_dem_fps_danco.shp'
# dems_only = False
# skip_ortho = False
# flat = False # do not create subdirectories for DEM strips
# dryrun = False
# dest_parent_dir = r'V:\pgc\data\scratch\jeff\ms\2020apr30\dems'