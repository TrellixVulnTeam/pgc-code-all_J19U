# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import re
import subprocess
from subprocess import PIPE
import sys

from misc_utils.logging_utils import create_logger, LOGGING_CONFIG
from misc_utils.RasterWrapper import Raster
from dem_utils.dem_rmse import dem_rmse
from dem_utils.rmse_compare import rmse_compare



# INPUTS
# dem1 = r'V:\pgc\data\scratch\jeff\ms\dems\clip\WV02_20130629_1030010023174900_103001002452E500_seg2_2m_dem_clip.tif'
# dem2 = r'V:\pgc\data\scratch\jeff\ms\dems\clip\WV02_20170410_1030010067C5FE00_1030010068B87F00_seg1_2m_dem_clip.tif'
# dem3 = r''

# out_dir = r'V:\pgc\data\scratch\jeff\ms\dems\pca'


def main(dem1, dem2, out_dir, rmse=False, warp=False, dryrun=False, verbose=False):
    """
    Aligns DEMs and writes outputs to out_dir.

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to the reference DEM.
    dem2 : os.path.abspath
        Path to the DEM to translate.
    out_dir : os.path.abspath
        Path to write alignment files to.

    Returns
    -------
    None.

    """
    # TODO: Add support for multiple DEMs using n-align

    # Logging setup
    if verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'

    logging.config.dictConfig(LOGGING_CONFIG(handler_level))
    logger = logging.getLogger(__name__)
    print('logger level: {}'.format(logger.level))
    # logger.setLevel(handler_level)
    # logging.level = 0


    # PARAMETERS
    dem1_name = os.path.basename(dem1).split('.')[0][:13]
    dem2_name = os.path.basename(dem2).split('.')[0][:13]
    combo_name = '{}_{}'.format(dem1_name, dem2_name)
    # Regex for cleaning streaming text outputs
    clean_re = re.compile('(?:\s+|\t+|\n+)')
    
    
    #### FUNCTION DEFINITION ####
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        # proc.wait()
        output, error = proc.communicate()
        logger.debug('Output: {}'.format(output.decode()))
        logger.debug('Err: {}'.format(error.decode()))
    
    
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
    if res1 != res2:
        logger.warning('Resolutions do not match. Defaulting to DEM1.\nDEM1: {}\nDEM2: {}'.format(res1, res2))
    if nodata1 != nodata2:
        logger.warning('No data values do not match. Defaulting to DEM1.\nDEM1:{}\nDEM2: {}'.format(nodata1, nodata2))
    if srs1.IsSame(srs2) == 0: # GDAL method for spatial reference comparison
        logger.warning('Spatial references do not match. Defaulting to DEM1.\nDEM1:\n{}\n\nDEM2:\n{}\n'.format(srs1, srs2))
        if warp == True:
            logger.warning('Reprojecting not yet supported, exiting.')
            sys.exit(-1)
    
    # RMSE if requested
    if rmse:
        logger.info('Computing pre-alignment RMSE for {}...'.format(combo_name))
        rmse_outfile = os.path.join(out_dir, '{}_preRMSE.txt'.format(combo_name))
        save_plot = os.path.join(out_dir, '{}_preRMSE.png'.format(combo_name))
        if dryrun:
            rmse_outfile = None
            save_plot = None
        pre_rmse = dem_rmse(dem1, dem2, 
                            outfile=rmse_outfile,
                            plot=True,
                            save_plot=save_plot)
        logger.info('RMSE prior to alignment: {:.2f}\n'.format(pre_rmse))
    
    
    #### PC_ALIGN ####
    logger.info('Running pc_align...')
    max_displacement = 10
    threads = 16
    prefix = '{}'.format(dem2_name)
    
    pca_command = """pc_align --save-transformed-source-points
                    --max-displacement {}
                    --threads {}
                    -o {}
                    {} {}""".format(max_displacement,
                                    threads,
                                    os.path.join(out_dir, prefix),
                                    dem1,
                                    dem2)
    
    # Clean up command
    pca_command = clean_re.sub(' ', pca_command)
    logger.debug('pc_align command:\n{}\n'.format(pca_command))
    if not dryrun:
        run_subprocess(pca_command)
    
        # Read contents of log file and report translation information
        log_file = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if '-log-pc_align' in f][0]
        with open(log_file, 'r') as lf:
            content = lf.readlines()
            trans_info = 'Translation information:\n'
            for line in content:
                if 'North-East-Down' in line or 'magnitude' in line:
                    relevent = '{}\n'.format(line.split('Translation vector')[1])
                    relevent = ' '.join(relevent.split('Vector3'))
                    trans_info += relevent
            logger.debug(trans_info)
    
    
    #### POINT2DEM ####
    logger.info('Running point2dem...')
    out_name = os.path.join(out_dir, '{}_pca'.format(dem2_name))
    trans_source = os.path.join(out_dir, '{}-trans_source.tif'.format(prefix))
    p2d_command = """point2dem 
                    --threads {}
                    --nodata-value {}
                    -s {}
                    -o {}
                    {}""".format(threads, nodata1, res1, out_name, trans_source)
    p2d_command = clean_re.sub(' ', p2d_command)
    logger.debug('point2dem command:\n{}\n'.format(p2d_command))
    if not dryrun:
        run_subprocess(p2d_command)
    
    if rmse:
        logger.info('Computing post-alignment RMSE...')
        out_dem = os.path.join(out_dir, '{}-DEM.tif'.format(out_name))
        rmse_outfile = os.path.join(out_dir, '{}_postRMSE.txt'.format(combo_name))
        save_plot = os.path.join(out_dir, '{}_postRMSE.png'.format(combo_name))
        if not dryrun:
            post_rmse = dem_rmse(dem1, out_dem, 
                                outfile=rmse_outfile,
                                plot=True,
                                save_plot=save_plot)
            logger.info('RMSE after alignment: {:.2f}\n'.format(post_rmse))
        logger.info('Comparing RMSE...')
        rmse_compare_outfile = os.path.join(out_dir, '{}_compareRMSE.txt'.format(combo_name))
        rmse_compare_save_plot = os.path.join(out_dir, '{}_compareRMSE.png'.format(combo_name))
        rmse_compare(dem1, dem2, out_dem, 
        			 outfile=rmse_compare_outfile,
        			 plot=True,
        			 save_plot=rmse_compare_save_plot)

# main(dem1, dem2, out_dir, rmse=True, verbose=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('dem1', type=os.path.abspath,
                        help='Path to the DEM to align to, the reference DEM.')
    parser.add_argument('dem2', type=os.path.abspath,
                        help='Path to the DEM to translate.')
    parser.add_argument('out_dir', type=os.path.abspath,
                        help='Path to write output files to.')
    parser.add_argument('--rmse', action='store_true',
                        help='Compute RMSE before and after alignment.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging to DEBUG')
    
    args = parser.parse_args()
    
    dem1 = args.dem1
    dem2 = args.dem2
    out_dir = args.out_dir
    rmse = args.rmse
    dryrun = args.dryrun
    verbose = args.verbose
    
    
    main(dem1, dem2, out_dir, rmse=rmse, dryrun=dryrun, verbose=verbose)
    