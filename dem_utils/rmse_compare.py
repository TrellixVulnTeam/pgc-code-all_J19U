import argparse
import logging.config
import numpy as np
import os
import random
import matplotlib.pyplot as plt

from osgeo import gdal, osr
import geopandas as gpd
from shapely.geometry import Point


from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger, LOGGING_CONFIG
from misc_utils.gdal_tools import clip_minbb


logging.config.dictConfig(LOGGING_CONFIG('DEBUG'))
logger = logging.getLogger(__name__)

dem1_path = r''
dem2_path = r''
dem2pca_path = r''


def rmse_compare(dem1_path, dem2_path, dem2pca_path, outfile=None, plot=False,
                 save_plot=None, show_plot=False, bins=10, log_scale=True):
    # Load DEMs as arrays
    logger.info('Loading DEMs...')
    dem1 = Raster(dem1_path)
    dem2 = Raster(dem2_path)
    dem2pca = Raster(dem2pca_path)

    if dem1.geotransform != dem2.geotransform or dem1.geotransform != dem2pca.geotransform:
        logger.warning('''DEM geotransforms do not match. 
                          Clipping to minimum bounding box in memory....''')
        dem1 = None
        dem2 = None
        clipped = clip_minbb(rasters=[dem1_path, dem2_path, dem2pca_path],
                             in_mem=True,
                             out_format='vrt')
        logger.debug('Clipping complete. Reloading DEMs...')
        dem1 = Raster(clipped[0])
        arr1 = dem1.MaskedArray
        dem1 = None
        logger.debug('DEM1 loaded and array extracted...')
        dem2 = Raster(clipped[1])
        arr2 = dem2.MaskedArray
        dem2 = None
        logger.debug('DEM2 loaded and array extracted...')
        dem2pca = Raster(clipped[2])
        arr2pca = dem2pca.MaskedArray

    else:
        arr1 = dem1.MaskedArray
        dem1 = None
        arr2 = dem2.MaskedArray
        dem2 = None
        arr2pca = dem2pca.MaskedArray
        dem2pca = None


    #### PRE-ALIGNMENT ####
    # Compute RMSE 
    logger.info('Computing RMSE pre-alignment...')
    diffs = arr1 - arr2

    sq_diff = diffs**2
    mean_sq = sq_diff.sum() / sq_diff.count()
    rmse = np.sqrt(mean_sq)

    # Report differences
    diffs_valid_count = diffs.count()
    min_diff = diffs.min()
    max_diff = diffs.max()
    logger.debug('Minimum difference: {:.2f}'.format(min_diff))
    logger.debug('Maximum difference: {:.2f}'.format(max_diff))
    logger.debug('Pixels considered: {:,}'.format(diffs_valid_count))
    logger.info('RMSE: {:.2f}'.format(rmse))

    # Write text file of results
    if outfile:
        with open(outfile, 'w') as of:
            of.write("DEM1: {}\n".format(dem1_path))
            of.write("DEM2: {}\n".format(dem2_path))
            of.write('RMSE: {:.2f}\n'.format(rmse))
            of.write('Pixels considered: {:,}\n'.format(diffs_valid_count))
            of.write('Minimum difference: {:.2f}\n'.format(min_diff))
            of.write('Maximum difference: {:.2f}\n'.format(max_diff))


    #### POST ALIGNMENT ####
    # Compute RMSE
    logger.info('Computing RMSE pre-alignment...')
    diffs_pca = arr1 - arr2pca

    sq_diff_pca = diffs_pca**2
    mean_sq_pca = sq_diff_pca.sum() / sq_diff_pca.count()
    rmse_pca = np.sqrt(mean_sq_pca)

    # Report differences
    diffs_pca_valid_count = diffs_pca.count()
    min_diff_pca = diffs_pca.min()
    max_diff_pca = diffs_pca.max()
    logger.debug('Minimum difference: {:.2f}'.format(min_diff_pca))
    logger.debug('Maximum difference: {:.2f}'.format(max_diff_pca))
    logger.debug('Pixels considered: {:,}'.format(diffs_pca_valid_count))
    logger.info('RMSE: {:.2f}'.format(rmse_pca))

    # Add to text file of results
    if outfile:
        with open(outfile, 'a') as of:
            of.write("DEM1: {}\n".format(dem1_path))
            of.write("DEM2pca: {}\n".format(dem2pca_path))
            of.write('RMSEpca: {:.2f}\n'.format(rmse_pca))
            of.write('Pixels considered pca: {:,}\n'.format(diffs_pca_valid_count))
            of.write('Minimum difference pca: {:.2f}\n'.format(min_diff_pca))
            of.write('Maximum difference pca: {:.2f}\n'.format(max_diff_pca))


    # Plot results
    # TODO: Add legend and RMSE annotations
    if plot:
        plt.style.use('ggplot')
        fig, ax = plt.subplots(1,1)
        ax.hist(diffs.compressed().flatten(), log=log_scale, bins=bins, edgecolor='white', 
                alpha=0.5)
        ax.hist(diffs_pca.compressed().flatten(), log=log_scale, bins=bins, edgecolor='white', color='b',
                alpha=0.5)
        plt.tight_layout()
        if save_plot:
            plt.savefig(save_plot)
        if show_plot:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('dem1', type=os.path.abspath,
                        help='Path to first, reference DEM.')
    parser.add_argument('dem2', type=os.path.abspath,
                        help='Path to second, unaligned DEM.')
    parser.add_argument('dem2pca', type=os.path.abspath,
                        help='Path to aligned second DEM.')
    parser.add_argument('--outfile', type=os.path.abspath,
                        help='Path to write results to.')
    parser.add_argument('--plot', action='store_true')
    parser.add_argument('--save_plot', type=os.path.abspath,
                        help='Path to save figure to.')
    parser.add_argument('--show_fig', action='store_true',
                        help='Open plot in new window.')
    parser.add_argument('--bins', type=int, default=10,
                        help='Number of bins to use for histogram.')
    parser.add_argument('--no_log_scale', action='store_true',
                        help='Do not use log scale for counts of histogram.')

    args = parser.parse_args()

    dem1 = args.dem1
    dem2 = args.dem2
    dem2pca = args.dem2pca
    outfile = args.outfile
    plot = args.plot
    save_plot = args.save_plot
    show_fig = args.show_plot
    bins = args.bins
    log_scale = not args.no_log_scale # if no_log_scale is passed, log_scale should be False

    rmse_compare(dem1, dem2, dem2pca, 
                 outfile=outfile, 
                 plot=plot, 
                 save_plot=save_plot, 
                 show_fig=show_plot,
                 bins=bins,
                 log_scale=log_scale)

