# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 14:00:03 2020

@author: disbr007
"""
import argparse
import json
import logging.config
import os
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import geopandas as gpd
# import fiona
# import rasterio
from rasterstats import zonal_stats

from misc_utils.logging_utils import create_logger
from misc_utils.gdal_tools import auto_detect_ogr_driver


logger = create_logger(__name__, 'sh', 'INFO')


def load_stats_dict(stats_json):
    with open(stats_json) as jf:
        data = json.load(jf)
        # rasters = [d['path'] for n, d in data.items()]
        # names = [n for n, d in data.items()]
        # stats = [d['stats'] for n, d in data.items()]

        names = []
        rasters = []
        stats = []
        bands = []
        for n, d in data.items():
            names.append(n)
            rasters.append(d['path'])
            stats.append(d['stats'])
            if 'bands' in d.keys():
                bands.append(d['bands'])
            else:
                bands.append(None)

    return rasters, names, stats, bands


def calc_compactness(geometry):
    # Polsby - Popper Score - - 1 = circle
    compactness = (np.pi * 4 * geometry.area) / (geometry.boundary.length)**2
    return compactness


def apply_compactness(gdf, out_field='compact'):
    gdf[out_field] = gdf.geometry.apply(lambda x: calc_compactness(x))


def compute_stats(gdf, raster, stats_dict, band=None):
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
    logger.info('Computing {} on raster:\n{}'.format(' '.join(stats_dict.keys()), raster))
    if band:
        logger.info('Band: {}'.format(band))
        gdf = gdf.join(pd.DataFrame(zonal_stats(gdf['geometry'], raster,
                                                stats=[k for k in stats_dict.keys()],
                                                band=band))
                       .rename(columns=stats_dict),
                       how='left')
    else:
        gdf = gdf.join(pd.DataFrame(zonal_stats(gdf['geometry'], raster,
                                                stats=[k for k in stats_dict.keys()],))
                       .rename(columns=stats_dict),
                       how='left')
    return gdf


def calc_zonal_stats(shp, rasters, names, 
                stats=['min', 'max', 'mean', 'count', 'median'],
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
    # TODO: Fix logic here, what is a bad path is passed?
    if len(rasters) == 1:
        if os.path.exists(rasters[0]):
            logger.info('Reading raster file...')
            ext = os.path.splitext(rasters[0])[1]
            if ext == '.txt':
                # Assume text file of raster paths, read into list
                logger.info('Reading rasters from text file: {}'.format(rasters[0]))
                with open(rasters[0], 'r') as src:
                    content = src.readlines()
                    rasters = [c.strip() for c in content]
                    rasters, names = zip(*(r.split("~") for r in rasters))
                    logger.info('Located rasters:'.format('\n'.join(rasters)))
                    for r, n in zip(rasters, names):
                        logger.info('{}: {}'.format(n, r))
                # Create list of lists of stats passed, one for each raster
                stats = [stats for i in range(len(rasters))]
            elif ext == '.json':
                logger.info('Reading rasters from json file: {}'.format(rasters[0]))
                rasters, names, stats, bands = load_stats_dict(rasters[0])
            else:
                # Raster paths directly passed
                stats = [stats for i in range(len(rasters))]

    # Iterate rasters and compute stats for each
    for r, n, s, bs in zip(rasters, names, stats, bands):
        if bs is None:
            stats_dict = {x: '{}_{}'.format(n, x) for x in s}
            seg = compute_stats(gdf=seg, raster=r, stats_dict=stats_dict)
        else:
            # Compute stats for each band
            for b in bs:
                stats_dict = {x: '{}b{}_{}'.format(n, b, x) for x in s}
                seg = compute_stats(gdf=seg, raster=r, stats_dict=stats_dict, band=b)
    
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
    driver = auto_detect_ogr_driver(out_path, name_only=True)
    seg.to_file(out_path, driver=driver)
    
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
                                Or path to .txt file of raster paths (one per line),
                                or path to .json file in format:
                                {"name": {"path": "C:\\raster", "stats":["mean", "min"]}}""")
                        # TODO: Adjust to take json of {raster1: {path: C:\raster.tif, name: raster, stats: mean, max,}}
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
                     area=args.area,
                     compactness=args.compactness,
                     out_path=args.out_path)
