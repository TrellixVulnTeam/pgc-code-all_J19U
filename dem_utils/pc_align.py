# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import argparse
import datetime
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
    

def calc_rmse(dem1, dem2, max_diff=None, save=False, out_dir=None, 
              long_name=False, suffix=None):
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
    save : BOOL
        True to save plots.
    out_dir : os.path.abspath
        Path to save plots to, if desired.
    long_name : BOOL
        Use long combo names.
    suffix : STR
        String to append to 
        
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
    cn = combo_name(dem1, dem2, long_name=long_name)
    if suffix:
        cn += suffix
    
    logger.info('Computing pre-alignment RMSE for {}...'.format(cn))
    if save and out_dir:
        save_plot = os.path.join(out_dir, '{}_RMSE.png'.format(cn))
    else:
        save_plot = None
    pre_rmse = dem_rmse(dem1, dem2, 
                        max_diff=max_diff,
                        plot=save,
                        save_plot=save_plot)
    logger.info('RMSE prior to alignment: {:.2f}\n'.format(pre_rmse))


def run_pc_align(dem1, dem2, max_diff, out_dir, threads=16,
                 pc_align_prefix=None,
                 long_name=False,
                 dryrun=False):
    
    #### PC_ALIGN ####
    logger.info('Running pc_align...')
    max_displacement = max_diff
    if not pc_align_prefix:
        pc_align_prefix = '{}'.format(dem_name(dem2, long_name=long_name))
    
    pca_command = """pc_align 
                    --save-transformed-source-points
                    --compute-translation-only
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
    


def cleanup(out_dir):
    """Remove files created by pc_align from the given directory"""
    logger.debug('Removing pc_align files...')
    pc_align_sfx = ['-beg_errors', '-end_errors', 'inverse-transform',
                    'iterationInfo', '-log-pc_align', 'trans_source',
                    'transform']
    
    pca_files = [os.path.join(out_dir, f) for f in os.listdir(out_dir)
                 if any([s in f for s in pc_align_sfx])]
    logger.debug('pc_align files found: {}\n{}'.format(len(pca_files), '\n'.join(pca_files)))
    
    for pf in pca_files:
        try:
            os.remove(pf)
        except Exception as e:
            logger.error('Could not remove file: {}'.format(pf))
            logger.error(e)
    logger.debug('pc_align files removed')
    
    
def pc_align_dems(dems, out_dir, rmse=False, max_diff=10, threads=16,
                  skip_cleanup=False,
                  dryrun=False):
    """
    Wrapper function to run pc_align for a number of DEMs, including applying
    the translation and computing RMSE if desired.

    Parameters
    ----------
    dems : list
        List of paths to DEMs. First DEM is the reference DEM.
    out_dir : os.path.abspath
        Directory to write output files to.
    rmse : BOOL, optional
        True to compute and report RMSE before and after running pc_align. The default is False.
    rmse_plots : BOOL, optional
        True to save plots to out_dir. The default is False.
    max_diff : FLOAT, optional
        Maximum difference to consider in both pc_align and RMSE calculations. The default is 10.
    dryrun : BOOL, optional
        True to print without running. The default is False.

    Returns
    -------
    LIST . List of paths to translated DEMs.

    """
    # TODO: Write the wrapper

    # Determine reference dem
    ref_dem = dems[0]
    logger.info('Reference DEM: {}'.format(ref_dem))
    
    # Check if any of the 'short names' (1st 13 characters) would be the same
    long_names = [combo_name(ref_dem, dem) for dem in dems[1:]]
    use_long_names = len(long_names) == len(set(long_names))
    
    for dem in dems[1:]:
        logger.info('Aligning DEM: {}'.format(dem))
        # Check for meta-data matches (resolution, NoData value, SRS) - issues reported to log
        meta_check = check_dem_meta(ref_dem, dem)
        if not meta_check['srs']:
            logger.error('Spatial references do not match. Exiting.')
            sys.exit()
        
        # Determine output name
        cn = combo_name(ref_dem, dem, long_name=use_long_names)
        
        # Calculate RMSE if desired
        if rmse:
            calc_rmse(ref_dem, dem, max_diff=max_diff, save=True, 
                      out_dir=out_dir, long_name=use_long_names,
                      suffix='_pre')
        
        # Run pc_align
        run_pc_align(ref_dem, dem, max_diff=max_diff, out_dir=out_dir,
                     pc_align_prefix=cn,
                     threads=threads)
        
        if not dryrun:
            # Read the translation vector from pc_align log file (dx, dy, dz)
            trans_vec = get_trans_vector(cn, out_dir=out_dir)
            # Apply the translation vector
            out_dem = os.path.join(out_dir, '{}-pcaDEM.tif'.format(cn))
            apply_trans(dem, trans_vec=trans_vec, out_path=out_dem)
    
    if not dryrun:
        # Copy the reference DEM to the output folder
        logger.info('Copying reference DEM to output location.')
        ref_dem_copy = os.path.join(out_dir, '{}_pcarefDEM'.format(os.path.splitext(ref_dem)[0]))
        shutil.copyfile(ref_dem, ref_dem_copy)
        if not skip_cleanup:
            cleanup(out_dir=out_dir)

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--dems', nargs='+', type=os.path.abspath,
                        help="""Paths to the DEMs to align or directory of DEMs. The first DEM
                                passed will be the reference DEM.""")
    parser.add_argument('--dem_ext', type=str, default='tif',
                        help="""If dems is a directory, the extension the DEMs share, used
                              to select DEM files.""")
    parser.add_argument('--out_dir', type=os.path.abspath,
                        help='Path to write output files to.')
    parser.add_argument('--rmse', action='store_true',
                        help='Compute RMSE before and after alignment.')
    parser.add_argument('--max_diff', type=int, default=10,
                        help='Maximum difference to use in pc_align and RMSE calculations.')
    parser.add_argument('--threads', type=int, default=16,
                        help='Number of threads to use during pc_align computation.')
    parser.add_argument('--skip_cleanup', action='store_true',
                        help='Do not remove pc_align files.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging to DEBUG')
    
    args = parser.parse_args()
    
    dems = args.dems
    dem_ext = args.dem_ext
    out_dir = args.out_dir
    rmse = args.rmse
    max_diff = args.max_diff
    threads = args.threads
    skip_cleanup = args.skip_cleanup
    dryrun = args.dryrun
    verbose = args.verbose

    pc_align_dems(dems=dems, out_dir=out_dir, rmse=rmse, 
                  max_diff=max_diff, threads=threads,
                  skip_cleanup=skip_cleanup,
                  dryrun=dryrun)
    
    if verbose:
        log_lvl = 'DEBUG'
    else:
        log_lvl = 'INFO'
    logger = create_logger(__name__, 'sh', log_lvl)
    now = datetime.datetime.now().strftime('%Y%b%dt%H%M%S')
    log_file = os.path.join(out_dir, 'pca_log{}.txt'.format(now))
    logger = create_logger(__name__, 'fh', 'INFO', filename=log_file)