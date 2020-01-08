# -*- coding: utf-8 -*-
"""
Created on Sun Jan  5 18:38:32 2020

@author: disbr007
"""
import argparse
import os
import shutil
import numpy as np
from copy import deepcopy

from osgeo import gdal
from tqdm import tqdm

from logging_utils import create_logger


# Inputs
input_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\clipped'
ext = 'tif'
band = 1 # band to check if all no data TODO: add option to check all bands


logger = create_logger('delete_nodata', 'sh', 'INFO')


def delete_NoData(input_dir, ext='tif', band=1, dryrun=False):
    logger.info('Parsing {} for NoData only rasters...'.format(input_dir))
    # Loop over input directory and delete and rasters that are entirely* no data
    for root, dirs, files in os.walk(input_dir):
        file_paths_master = [os.path.join(root, f) for f in files]
        file_paths = deepcopy(file_paths_master)    
        
        for fp in file_paths:
            if fp.endswith(ext):
                logger.info('Checking {}'.format(os.path.basename(fp)))
                # Get filename w/o extension to delete metadata files
                filename = os.path.basename(fp).split('.')[0]
                # Check if any non-NoData values exist
                ds = gdal.Open(fp)
                no_data_val = ds.GetRasterBand(band).GetNoDataValue()
                array = ds.ReadAsArray()
                ds = None
                valid_data = np.any(array != no_data_val)
                
                if valid_data == False:
                    logger.info('{} contains all NoData values, deleting...'.format(fp))            
                    matching_files = [fp for fp in file_paths_master
                                      if os.path.basename(fp).split('.')[0]==filename]
                    for mf in matching_files:
                        if not dryrun:
                            os.remove(mf)
                elif valid_data == True:
                    logger.info('Keeping {}'.format(fp))
                else:
                    logger.info('Unk')
                
                
if __name__ == '__main__':
    script_desc = """Parses the input directory RECURSIVELY and deletes any 
                     rasters with the matching extension that contain only
                     NoData values."""
                     
    parser = argparse.ArgumentParser(description=script_desc)
    
    parser.add_argument('input_directory', type=os.path.abspath,
                        help='Path to directory to check for NoData rasters.')
    parser.add_argument('--ext', type=str, default='tif',
                        help='Extension of rasters to check')
    parser.add_argument('--band', type=int, default=1,
                        help='Band to check for NoData only values.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print messages but do not run.')
    args = parser.parse_args()
    
    logger.info('Starting...')
    
    delete_NoData(args.input_directory, ext=args.ext, band=args.band)