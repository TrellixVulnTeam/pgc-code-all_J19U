# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 14:00:03 2020

@author: disbr007
"""
import argparse
import logging.config
import os
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import geopandas as gpd
# import fiona
# import rasterio
from rasterstats import zonal_stats

from misc_utils.logging_utils import LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)


#### Inputs
# Segmentation vector
seg_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500.shp'
# Path to write segmentation vector with added statistics columns
outpath = os.path.join(os.path.dirname(seg_path),
                       '{}_stats.shp'.format(os.path.basename(seg_path).split('.')[0]))
# Paths to rasters to use to compute statistics
roughness_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\roughness\dem_WV02_20150906_roughness.tif'
tpi31_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\tpi\WV02_20150906_tpi31.tif'
tpi41_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\tpi\WV02_20150906_tpi41.tif'
tpi81_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\tpi\WV02_20150906_tpi81.tif'
slope_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\slope\WV02_20150906_pcatdmx_slope.tif'
diff_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\diffs\WV02_20150906_WV02_20130711_diff.tif'
ndvi_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\imagery\ndvi_ps\WV02_20150906203203_1030010048B0FA00_15SEP06203203-M1BS-500447187090_01_P008_u16mr3413_pansh_ndvi.tif'
diff_ndvi_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\imagery\diff_ndvi_ps\diff_ndvi_ps_WV02_20150906_WV02_20130711.tif'
# Path to digitized thaw slumps for examining statistics
tks_bounds_p = r'E:\disbr007\umn\ms\shapefile\tk_loc\digitized_thaw_slumps.shp'


def compute_stats(gdf, raster, stats_dict):
    """
    Computes statistics for each polygon in geodataframe
    based on raster. Statistics to be computed are the keys
    in the stats_dict, and the renamed columns are the values.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame of polygons to compute statistics over.
    raster : os.path.abspath | rasterio.raster
        Raster to compute statistics from.
    stats_dict : DICT
        Dictionary of stat:renamed_col pairs.
        Stats must be one of: min, max, median. sum, std,
                              unique, range, percentile_<q>
                              OR custom function

    Returns
    -------
    The geodataframe with added columns.

    """
    logger.info('Computing {} on raster:\n{}...'.format(' '.join(stats_dict.keys()), raster))
    gdf = gdf.join(pd.DataFrame(zonal_stats(gdf['geometry'], raster, 
                                        stats=[k for k in stats_dict.keys()]))
                   .rename(columns=stats_dict),
               how='left')

    return gdf


def zonal_stats(shp,
                rasters, names, 
                stats=['min', 'max', 'mean', 'count', 'median' ],
                area=True,
                compactness=True,
                out_path=None):
    """
    Calculate zonal statistics on the given vector file
    for each raster provided.

    Parameters
    ----------
    shp : os.path.abspath
        Vector file to compute zonal statistics for the features in.
    out_path : os.path.abspath
        Path to write vector file with computed stats. Default is to
        add '_stats' suffix before file extension.
    rasters : list or os.path.abspath
        List of rasters to compute zonal statistics for.
        Or path to .txt file of raster paths (one per line).
    names : list
        List of names to use as prefixes for created stats. Order
        is order of rasters.
    stats : list, optional
        List of statistics to calculate. The default is None.
    area : bool
        True to also compute area of each feature in units of
        projection.
    compactness : bool
        True to also compute compactness of each object
    Returns
    -------
    None.

    """
    # Load data
    logger.info('Reading in segments...')
    seg = gpd.read_file(seg_path)
    logger.info('Segments found: {:,}'.format(len(seg)))
    
    # Determine rasters input type
    if len(rasters) == 1:
        if os.path.exists(rasters[0]):
            ext = os.path.splitext(rasters[0])[1]
            if ext == '.txt.':
                # Assume text file of raster paths, read into list
                with open(rasters[0], 'r') as src:
                    content = src.readlines()
                    rasters = [c.strip() for c in content]
                
        
    # Iterate rasters and compute stats for each
    for r, n in zip(rasters, names):
        logger.info('Computing zonal statistics for {}'.format(os.path.basename(r)))
        stats_dict = {s: '{}_{}'.format(n, s) for s in stats}
        seg = compute_stats(gdf=seg, raster=r, stats_dict=stats_dict)
    
    # Area recording
    if area:
        seg['area_zs'] = seg.geometry.area
    
    # Compactness: Polsby-Popper Score -- 1 = circle
    if compactness:
        seg['compact'] = (np.pi * 4 * seg.geometry.area) / (seg.geometry.boundary.length)**2

    # Write segments with stats to new shapefile
    if not out_path:
        out_path = os.path.join(os.path.dirname(seg_path),
                       '{}_stats.shp'.format(os.path.basename(seg_path).split('.')[0]))
    logger.info('Writing segments with statistics to: {}'.format(out_path))
    seg.to_file(out_path)
    
    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_shp',
                        type=os.path.abspath,
                        help='Vector file to compute zonal statistics for the features in.')
    parser.add_argument('-o', '--out_path',
                        type=os.path.abspath,
                        help="""Path to write vector file with computed stats. Default is to
                                add '_stats' suffix before file extension.""")
    parser.add_argument('-r', '--rasters',
                        nargs='+',
                        type=os.path.abspath,
                        help="""List of rasters to compute zonal statistics for.
                                Or path to .txt file of raster paths (one per line).""")
    parser.add_argument('-n', '--names',
                        type=str,
                        nargs='+',
                        help="""List of names to use as prefixes for created stats fields.
                                Length must match number of rasters supplied. Order is
                                the order of the rasters to apply prefix names for. E.g.:
                                'ndvi' -> 'ndvi_mean', 'ndvi_min', etc.""")
    parser.add_argument('-s', '--stats',
                        type=str,
                        nargs='+',
                        default=['min', 'max', 'mean', 'count', 'median'],
                        help='List of statistics to compute.')
    parser.add_argument('-a', '--area',
                        action='store_true',
                        help='Use to compute an area field.')
    parser.add_argument('-c', '--compactness',
                        action='store_true',
                        help='Use to compute a compactness field.')
    
    args = parser.parse_args
    
    zonal_stats(shp=args.input_shp,
                rasters=args.rasters,
                names=args.names,
                stats=args.stats,
                area=args.compactness,
                compactness=args.compactness,
                out_path=args.out_path)

# # Load data
# logger.info('Reading in segments...')
# seg = gpd.read_file(seg_path)
# logger.info('Segments found: {:,}'.format(len(seg)))

# # Compute zonal statistics from rasters
# logger.info('Computing statistics...')
# tpi_stats = ['min', 'max', 'mean', 'std']
# tpi31_stats = {k: 'tpi31_{}'.format(k) for k in tpi_stats}
# tpi41_stats = {k: 'tpi41_{}'.format(k) for k in tpi_stats}
# tpi81_stats = {k: 'tpi81_{}'.format(k) for k in tpi_stats}

# roughness_stats = {'mean': 'rough_mean',
#                    'max': 'rough_max',
#                    'min': 'rough_min'}

# slope_stats = {'mean': 'slope_mean', 
#                'max': 'slope_max',
#                'std': 'slope_std'}

# diff_stats = {'mean': 'diff_mean',
#               'max': 'diff_max',
#               'min': 'diff_min'}

# diff_ndvi_stats = {'mean': 'diffndvi_mean',
#                    'min': 'diffndvi_min',
#                    'max': 'diffndvi_max'}

# ndvi_stats = {'mean': 'ndvi_mean',
#               'min': 'ndvi_min',
#               'max': 'ndvi_max'}

# stats_on = [(roughness_path, roughness_stats),
#             (tpi31_path, tpi31_stats), 
#             (tpi41_path, tpi41_stats),
#             (tpi81_path, tpi81_stats),
#             (slope_path, slope_stats),
#             (diff_path, diff_stats),
#             (diff_ndvi_path, diff_ndvi_stats),
#             (ndvi_path, ndvi_stats)]


# for raster, stats in stats_on:
#     seg = compute_stats(seg, raster, stats)
# logger.info('Zonal statistics computed.')

# #### Compute geometric statistics
# # Area
# seg['area_m'] = seg.geometry.area
# # Compactness: Polsby-Popper Score -- 1 = circle
# seg['compact'] = (np.pi * 4 * seg.geometry.area) / (seg.geometry.boundary.length)**2


# # Write segments with stats to new shapefile
# logger.info('Writing segments with statistics to: {}'.format(outpath))
# seg.to_file(outpath)
# logger.info('Done.')