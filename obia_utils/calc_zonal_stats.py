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


def calc_zonal_stats(shp, rasters, names, 
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
    seg = gpd.read_file(shp)
    logger.info('Segments found: {:,}'.format(len(seg)))
    
    # Determine rasters input type
    if len(rasters) == 1:
        if os.path.exists(rasters[0]):
            ext = os.path.splitext(rasters[0])[1]
            if ext == '.txt':
                # Assume text file of raster paths, read into list
                logger.info('Reading rasters from file: {}'.format(rasters[0]))
                with open(rasters[0], 'r') as src:
                    content = src.readlines()
                    rasters = [c.strip() for c in content]
                    rasters, names = zip(*(r.split("~") for r in rasters))
                    logger.info('Located rasters:'.format('\n'.join(rasters)))
                    for r, n in zip(rasters, names):
                        logger.info('{}: {}'.format(n, r))


    # Iterate rasters and compute stats for each
    for r, n in zip(rasters, names):
        # logger.info('Computing zonal statistics for {}'.format(os.path.basename(r)))
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
        out_path = os.path.join(os.path.dirname(shp),
                       '{}_stats.shp'.format(os.path.basename(shp).split('.')[0]))
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
    
    args = parser.parse_args()
    
    calc_zonal_stats(shp=args.input_shp,
                     rasters=args.rasters,
                     names=args.names,
                     stats=args.stats,
                     area=args.compactness,
                     compactness=args.compactness,
                     out_path=args.out_path)
