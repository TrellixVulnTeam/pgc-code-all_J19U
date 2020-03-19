# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import re
import shutil
import subprocess
from subprocess import PIPE
import sys

import geopandas as gpd
from osgeo import gdal

from misc_utils.logging_utils import create_logger, LOGGING_CONFIG
from misc_utils.RasterWrapper import Raster
from dem_utils.dem_rmse import dem_rmse
from dem_utils.rmse_compare import rmse_compare


logger = create_logger(__name__, 'sh', 'DEBUG')
# TODO: Add log file location
# logger = create_logger(__name__, 'fh', 'INFO', filename='')

#### FUNCTION DEFINITION ####
def run_subprocess(command, clean=True):
    """Run a command as a subprocess, stream output back to logger"""
    if clean:
        clean_re = re.compile('(?:\s+|\t+|\n+)')
        command = clean_re.sub(' ', command)
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    # proc.wait()
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))
    
    return output, error
    

def check_dem_meta(dem1, dem2):
    """
    Compare metadata (NoData values, projection, resoultion) before running pc_align.

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to first (reference) DEM.
    dem2 : os.path.abspath
        Path to second (source / to be translated) DEM.

    Returns
    -------
    Dict. Bool values for 'resolution', 'nodata', 'srs'. True if match, False if not a match.

    """
    #### GET INFO ABOUT DEMS ####
    logger.info('Getting DEM metadata...')
    # DEM 1
    dem1_src = Raster(dem1)
    width1 = dem1_src.pixel_width
    height1 = dem1_src.pixel_height
    res1 = (abs(width1) + abs(height1)) / 2
    nodata1 = dem1_src.nodata_val
    srs1 = dem1_src.prj
    dem1_src = None
    dem1_info = 'resolution: {}\nnodata: {}\nsrs: {}\n'.format(res1, nodata1, srs1)
    logger.debug("""DEM1 Information:\n{}\n\n""".format(dem1_info))

    # DEM 2
    dem2_src = Raster(dem2)
    width2 = dem2_src.pixel_width
    height2 = dem2_src.pixel_height
    res2 = (abs(width2) + abs(height2)) / 2
    nodata2 = dem2_src.nodata_val
    srs2 = dem2_src.prj
    dem2_src = None
    dem2_info = 'resolution: {}\nnodata: {}\nsrs: {}'.format(res2, nodata2, srs2)
    logger.debug("""DEM2 Information:\n{}\n\n""".format(dem2_info))

    # Check for matches of resolution, nodata, spatial reference
    logger.info('Comparing DEM metadata (resolution, nodata value, spatial reference)...')
    meta_check = {'resolution': True, 'NoData': True, 'SRS': True}
    if res1 != res2:
        meta_check['resolution'] = False
        logger.warning('Resolutions do not match. Defaulting to DEM1.\nDEM1: {}\nDEM2: {}'.format(res1, res2))
    if nodata1 != nodata2:
        meta_check['nodata'] = False
        logger.warning('NoData values do not match. Defaulting to DEM1 NoData value when creating new DEM.\nDEM1:{}\nDEM2: {}'.format(nodata1, nodata2))
    if srs1.IsSame(srs2) == 0: # GDAL method for spatial reference comparison
        meta_check['srs'] = False
        logger.warning('Spatial references do not match. Defaulting to DEM1.\nDEM1:\n{}\n\nDEM2:\n{}\n'.format(srs1, srs2))
        
    return meta_check


def dem_name(dem, long_name=False):
    """Gets the 'name' of the dem path base. Full filename w/o extension if long_name"""
    # TODO: Revist naming
    if long_name:
        dem_name = os.path.basename(dem).split('.')[0]
    else:
        dem_name = os.path.basename(dem).split('.')[0][:13]
    
    return dem_name


def combo_name(dem1, dem2, long_name=False):
    """
    Create the output name for the translated DEM.

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to the first (reference) DEM.
    dem2 : os.path.abspath
        Path to the second (source / to be translated) DEM.
    long_name : BOOL
        True to use entire DEM filenames in output name. The default is False.

    Returns
    -------
    STR : combination of DEM names, with dem2 first, to use for outputs.

    """
    dem1_name = dem_name(dem1, long_name=long_name)
    dem2_name = dem_name(dem2, long_name=long_name)
    
    combo_name = '{}_{}'.format(dem2_name, dem1_name)
    
    return combo_name
    

def calc_rmse(dem1, dem2, max_diff=None, save=False, out_dir=None):
    """
    Calculate RMSE for two DEMs.

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to first (reference) DEM.
    dem2 : os.path.abspath
        Path to second (source / to be translated) DEM.
    max_diff : float
        Difference in DEMs to include in RMSE calculation.
    Returns
    -------
    None.

    """
    # TODO: Revist plotting. Can potentially do heatmap of DEM1 value vs. DEM2
    #       value.
    # TODO: Potentially write plots out to PDF file: 
    #       https://stackoverflow.com/questions/52234935/
    #       which-is-the-best-way-to-make-a-report-in-pdf-
    #       with-more-than-100-plots-with-pyth/52294604#
    #       52294604?newreg=448b576560e34a1aa40cef7b0d1b6f84
    logger.info('Computing pre-alignment RMSE for {}...'.format(combo_name))
    rmse_outfile = os.path.join(out_dir, '{}_preRMSE.txt'.format(combo_name))
    save_plot = os.path.join(out_dir, '{}_preRMSE.png'.format(combo_name))
    pre_rmse = dem_rmse(dem1, dem2, 
                        max_diff=max_diff,
                        outfile=rmse_outfile,
                        plot=True,
                        save_plot=save_plot)
    logger.info('RMSE prior to alignment: {:.2f}\n'.format(pre_rmse))


def pc_align(dem1, dem2, max_diff, out_dir, threads=16, 
             long_name=False,
             dryrun=False):
    
    #### PC_ALIGN ####
    logger.info('Running pc_align...')
    max_displacement = max_diff
    pc_align_prefix = '{}'.format(dem_name(dem2, long_name=long_name))

    pca_command = """pc_align --save-transformed-source-points
                    --max-displacement {}
                    --threads {}
                    -o {}
                    {} {}""".format(max_displacement,
                                    threads,
                                    os.path.join(out_dir, pc_align_prefix),
                                    dem1,
                                    dem2)

    # Clean up command before passing
    clean_re = re.compile('(?:\s+|\t+|\n+)')
    pca_command = clean_re.sub(' ', pca_command)
    logger.debug('pc_align command:\n{}\n'.format(pca_command))
    if not dryrun:
        run_subprocess(pca_command)




def get_trans_vector(pc_align_prefix, out_dir):
    """Get the translation vector by reading output file from pc_align call"""
    
    # Find log file
    log_file = [os.path.join(out_dir, f) for f in os.listdir(out_dir) 
                if '{}-log-pc_align'.format(pc_align_prefix) in f]
    if not log_file:
        logger.error('Log file could not be located in directory: {}'.format(out_dir))
    elif len(log_file) > 1:
        logger.error('Multiple matching log files in directory: {}\n{}'.format(out_dir, log_file))
    else:
        log_file = log_file[0]
    logger.debug('pc_align log file located: {}'.format(log_file))
    
    # Read contents of log file and report translation information
    with open(log_file, 'r') as lf:
        content = lf.readlines()
        trans_info = 'Translation information:\n'
        for line in content:
            trans_vec_match = re.search('Translation vector \(North-East-Down, meters\): Vector3(.*)', line)
            if trans_vec_match:
                trans_vec = trans_vec_match.groups()[0]
                # Remove leading and trailing parenthesis, and convert to list of floats
                trans_vec = [float(vec) for vec in trans_vec.replace('(', '').replace(')', '').split(',')]
                # For logging
                trans_info += str(trans_vec)
                logger.debug(trans_info)
                break
        if not trans_vec_match:
            logger.error('Could not locate translation vector from pc_align log file:\n{}'.format(log_file))
    
    return trans_vec



def apply_trans(dem, trans_vec, out_path):
    """
    Apply a translation vector of format (dx, dy, dz) to DEM and save to out_path.
    Uses GDAL Translate which requires a the new window (ulx, uly, lrx, lry)

    Parameters
    ----------
    dem : os.path.abspath
        Path to the DEM to be translated.
    trans_vec : list/tuple
        Translation vector of format (dx, dy, dz).
    out_path : os.path.abspath
        Path to write the translated DEM to.

    Returns
    -------
    None.

    """
    # Get translation values
    dx, dy, dz = trans_vec
    
    # Open source DEM
    logger.debug('Reading source DEM for translation:\n{}'.format(dem))
    src = Raster(dem)
    
    # Compute new/translated bounds
    tulx = src.x_origin + dx
    tuly = src.y_origin + dy
    tlrx = tulx + src.x_sz * src.pixel_width
    tlry = tuly + src.y_sz * src.pixel_height
    trans_bounds = [tulx, tuly, tlrx, tlry]
    logger.debug('Translated bounds (ulx, uly, lrx, lry): {}'.format(trans_bounds))
    
    # Translate in x-y
    logger.debug('Applying translation in x-y...')
    temp_trans = r'/vsimem/temp_trans.vrt'
    trans_options = gdal.TranslateOptions(outputBounds=trans_bounds)
    gdal.Translate(out_path, dem, options=trans_options)
    logger.debug('DEM translated. Output: {}'.format(temp_trans))
    
    # Shift in z
    logger.debug('Applying translation in z...')
    src_arr = src.MaskedArray
    dst_arr = src_arr - dz
    logger.debug('Writing translated raster to: {}'.format(out_path))
    src.WriteArray(dst_arr, out_path)
    
    src = None
    logger.debug('Translation complete.')
    

dem = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\raw\WV02_20130711_1030010025A66E00_1030010025073200_seg1_2m_dem_clip.tif'
out = r'C:\temp\trans_test4.tif'
prefix = r'WV02_20130711_1030010025A66E00_1030010025073200_seg1_2m_dem_clip'
out_dir = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\pc_align\dems\pca_tdmx\misc'


trans_vec = get_trans_vector(prefix, out_dir)
apply_trans(dem, trans_vec, out)

# if warp is True:
#     # TODO: Add support for reprojecting
#     logger.warning('Reprojecting not yet supported, exiting.')
#     sys.exit(-1)