# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import argparse
# import logging.config
import os
import re
import shutil
import subprocess
from subprocess import PIPE
import sys

import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.RasterWrapper import Raster
from dem_rmse import dem_rmse
from rmse_compare import rmse_compare


# logger = create_logger(__name__, 'sh', 'INFO')

# handler_level = 'INFO'
# logging.config.dictConfig(LOGGING_CONFIG(handler_level))
# logger = logging.getLogger(__name__)


def pca_p2d(dem1, dem2, out_dir, max_diff_pca=10, max_diff_rmse=None,
            rmse=False, use_long_names=False, warp=False, dryrun=False):
    """
    Run pc_align, then point2dem on two input DEMs,
    optionally calculating before and after RMSE's,
    and/or clipping (?).

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to the reference DEM.
    dem2 : os.path.abspath
        Path to the DEM to translate.
    rmse : BOOL
        Calculate before and after RMSEs, including generating plots
        in out_dir
    use_long_names : BOOL
        Use full filenames for outputs. Otherwise just the short name
        of [sensor]_[date] is used. Set to True for filenames that
        do not confirm to PGC SETSM DEM naming convention.
    out_dir : os.path.abspath
        Path to write alignment files to.

    Returns
    -------
    None.

    """
    # PARAMETERS
    if use_long_names:
        dem1_name = os.path.basename(dem1).split('.')[0]
        dem2_name = os.path.basename(dem2).split('.')[0]
    else:
        dem1_name = os.path.basename(dem1).split('.')[0][:13]
        dem2_name = os.path.basename(dem2).split('.')[0][:13]
    combo_name = '{}_{}'.format(dem1_name, dem2_name)
    # Regex for cleaning streaming text outputs
    clean_re = re.compile('(?:\s+|\t+|\n+)')

    # FUNCTION DEFINITION
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        # proc.wait()
        output, error = proc.communicate()
        logger.debug('Output: {}'.format(output.decode()))
        logger.debug('Err: {}'.format(error.decode()))

    # GET INFO ABOUT DEMS
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
        logger.warning('NoData values do not match. Defaulting to DEM1 NoData value when creating new DEM.\nDEM1:{}\nDEM2: {}'.format(nodata1, nodata2))
    if srs1.IsSame(srs2) == 0:  # GDAL method for spatial reference comparison
        logger.warning('Spatial references do not match. Defaulting to DEM1.\nDEM1:\n{}\n\nDEM2:\n{}\n'.format(srs1, srs2))
        if warp is True:
            # TODO: Add support for reprojecting
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
                            max_diff=max_diff_rmse,
                            outfile=rmse_outfile,
                            plot=True,
                            save_plot=save_plot)
        logger.info('RMSE prior to alignment: {:.2f}\n'.format(pre_rmse))

    # PC_ALIGN
    logger.info('Running pc_align...')
    max_displacement = max_diff_pca
    # TODO: Make number threads an argument
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

        # Read contents of created log file and report translation information
        try:
            log_file = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if '-log-pc_align' in f][0]
        except IndexError:
            logger.error('No "-log-pc_align" file found. Did pc_align run successfuly?')
        with open(log_file, 'r') as lf:
            content = lf.readlines()
            trans_info = 'Translation information:\n'
            for line in content:
                trans_vec_match = re.search('Translation vector \(North-East-Down, meters\): Vector3(.*)', line)
                if trans_vec_match:
                    trans_vec = trans_vec_match.groups()[0]
                    trans_info += trans_vec.replace(',', ', ')
                    break
            logger.debug(trans_info)

    # POINT2DEM
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
                                 max_diff=max_diff_rmse,
                                 outfile=rmse_outfile,
                                 plot=True,
                                 save_plot=save_plot)
            logger.info('RMSE after alignment: {:.2f}\n'.format(post_rmse))
            logger.info('Comparing RMSE...')
            rmse_compare_outfile = os.path.join(out_dir, '{}_compareRMSE.txt'.format(combo_name))
            rmse_compare_save_plot = os.path.join(out_dir, '{}_compareRMSE.png'.format(combo_name))
            rmse_compare(dem1, dem2, out_dem,
                         max_diff=max_diff_rmse,
                         outfile=rmse_compare_outfile,
                         plot=True,
                         save_plot=rmse_compare_save_plot)

    # Move files into subdirectories
    # Move everything else
    misc_files = [os.path.join(out_dir, x) for x in os.listdir(out_dir)
                  if os.path.join(out_dir, x) not in [dem1, dem2, out_dem]]
    misc_dir = os.path.join(out_dir, 'misc')
    if not os.path.exists(misc_dir):
        os.makedirs(misc_dir)

    # print('Misc_files:\n{}'.format('\n'.join(misc_files)))
    for f in misc_files:
        shutil.move(f, misc_dir)

    # Move DEM
    # pc_align_dem_dir = os.path.join(out_dir, 'dem')
    # if not os.path.exists(pc_align_dem_dir):
    #     os.makedirs(pc_align_dem_dir)
    # shutil.move(out_dem, pc_align_dem_dir)


def main(dems, out_dir, max_diff_pca=10, max_diff_rmse=None,
         dem_ext='tif', dem_fp=None, rmse=False, warp=False, dryrun=False,
         verbose=False):
    """Align DEMs and writes outputs to out_dir."""
    # if verbose:
    #     handler_level = 'DEBUG'
    # else:
    #     handler_level = 'INFO'
    # logger = create_logger(__name__, 'sh',
    #                        handler_level=handler_level)
    # logger = create_logger(__name__, 'fh',
    #                       handler_level=handler_level)

    # If a directory is passed, get all files with extension: dem_ext
    # TODO: Make the DEM file selection better (support .vrt's, and more)
    if len(dems) == 1 and os.path.isdir(dems[0]):
        dems = [os.path.join(dems[0], x) for x in os.listdir(dems[0]) if x.endswith(dem_ext)]
    if dem_fp:
        logger.info('Determining reference DEM based on density in footprint...')
        dem_fp_df = gpd.read_file(dem_fp)
        dem_fp_df.sort_values(by=['density'], ascending=False, inplace=True)
        ref_dem_id = dem_fp_df['dem_id'].iloc[0]
        ref_dem_density = dem_fp_df['density'].iloc[0]
        logger.info('Reference DEM density: {:.3f}'.format(ref_dem_density))
        ref_dem = [x for x in dems if ref_dem_id in x]
        if len(ref_dem) != 1:
            if len(ref_dem) == 0:
                logger.error('Could not locate reference DEM from footprint ID.')
            else:
                logger.error('Multiple matching reference DEMs: {}'.format('\n'.join(ref_dem)))
            raise Exception
        ref_dem = ref_dem[0]
    else:
        ref_dem = dems[0]
        logger.info('Using first DEM as reference: {}'.format(ref_dem))

    logger.info("Reference DEM located:\n{}".format(ref_dem))
    other_dems = [x for x in dems if x is not ref_dem]
    logger.info("DEMs to align to reference:\n{}".format('\n'.join(other_dems)))

    # Check for same 'short-names' and if they exist use full filenames for outputs
    if True in [dn[:13] in [x[:13] for x in dems if x != dn] for dn in dems]:
        use_long_names = True

    for i, od in enumerate(other_dems):
        logger.info('Processing DEM {} / {}'.format(i + 1, len(other_dems)))
        logger.info('Running pc_align and point2dem on:\nReference DEM: {}\nSource DEM:    {}'.format(ref_dem, od))
        pca_p2d(ref_dem, od, max_diff_pca=max_diff_pca,
                max_diff_rmse=max_diff_rmse, out_dir=out_dir, rmse=rmse,
                use_long_names=use_long_names, warp=warp, dryrun=dryrun)

    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--dems', nargs='+', type=os.path.abspath,
                        help="""Paths to the DEMs to align or directory of DEMs. The first DEM
                                is used a the reference DEM.""")
    # parser.add_argument('dem2', type=os.path.abspath,
    #                     help='Path to the DEM to translate.')
    parser.add_argument('--dem_ext', type=str, default='tif',
                        help="""If dems is a directory, the extension the DEMs share, used
                              to select DEM files.""")
    parser.add_argument('--out_dir', type=os.path.abspath,
                        help='Path to write output files to.')
    parser.add_argument('--dem_fp', type=os.path.abspath,
                        help="""Path to footprint of DEMs containing at least two
                                fields:
                                    'dem_id' - dem_id
                                    'density' - match tag density
                                    The reference DEM will be the one with the highest density.
                                    If not provided, the first DEM passed to --dems will be the
                                    reference DEM.""")
    parser.add_argument('--rmse', action='store_true',
                        help='Compute RMSE before and after alignment.')
    parser.add_argument('--max_diff_pca', type=int, default=10,
                        help='Maximum difference to use in pc_align.')
    parser.add_argument('--max_diff_rmse', type=int, default=None,
                        help='Maximum difference to use in RMSE.')
    parser.add_argument('--logfile', type=os.path.abspath,
                        help='Path to write log file.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging to DEBUG')

    args = parser.parse_args()

    dems = args.dems
    dem_ext = args.dem_ext
    out_dir = args.out_dir
    dem_fp = args.dem_fp
    rmse = args.rmse
    max_diff_pca = args.max_diff_pca
    max_diff_rmse = args.max_diff_rmse
    logfile = args.logfile
    dryrun = args.dryrun
    verbose = args.verbose

    if verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'

    logger = create_logger(__name__, 'sh',
                           handler_level=handler_level)
    if logfile:
        logger = create_logger(__name__, 'fh',
                               handler_level=handler_level,
                               filename=logfile)

    main(dems, out_dir, max_diff_pca=max_diff_pca, max_diff_rmse=max_diff_rmse,
         dem_ext=dem_ext, dem_fp=dem_fp,
         rmse=rmse, dryrun=dryrun, verbose=verbose)
