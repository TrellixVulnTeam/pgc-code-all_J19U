# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 14:00:03 2020

@author: disbr007
"""

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


# Load data
logger.info('Reading in segments...')
seg = gpd.read_file(seg_path)
logger.info('Segments found: {:,}'.format(len(seg)))

# Compute zonal statistics from rasters
logger.info('Computing statistics...')
tpi_stats = ['min', 'max', 'mean', 'std']
tpi31_stats = {k: 'tpi31_{}'.format(k) for k in tpi_stats}
tpi41_stats = {k: 'tpi41_{}'.format(k) for k in tpi_stats}
tpi81_stats = {k: 'tpi81_{}'.format(k) for k in tpi_stats}

roughness_stats = {'mean': 'rough_mean',
                   'max': 'rough_max',
                   'min': 'rough_min'}

slope_stats = {'mean': 'slope_mean', 
               'max': 'slope_max',
               'std': 'slope_std'}

diff_stats = {'mean': 'diff_mean',
              'max': 'diff_max',
              'min': 'diff_min'}

diff_ndvi_stats = {'mean': 'diffndvi_mean',
                   'min': 'diffndvi_min',
                   'max': 'diffndvi_max'}

ndvi_stats = {'mean': 'ndvi_mean',
              'min': 'ndvi_min',
              'max': 'ndvi_max'}

stats_on = [(roughness_path, roughness_stats),
            (tpi31_path, tpi31_stats), 
            (tpi41_path, tpi41_stats),
            (tpi81_path, tpi81_stats),
            (slope_path, slope_stats),
            (diff_path, diff_stats),
            (diff_ndvi_path, diff_ndvi_stats),
            (ndvi_path, ndvi_stats)]


for raster, stats in stats_on:
    seg = compute_stats(seg, raster, stats)
logger.info('Zonal statistics computed.')

#### Compute geometric statistics
# Area
seg['area_m'] = seg.geometry.area
# Compactness: Polsby-Popper Score -- 1 = circle
seg['compact'] = (np.pi * 4 * seg.geometry.area) / (seg.geometry.boundary.length)**2


# Write segments with stats to new shapefile
logger.info('Writing segments with statistics to: {}'.format(outpath))
seg.to_file(outpath)
logger.info('Done.')


# for testing
# seg = gpd.read_file(outpath)

## Find segments in predrawn thermokarst boundaries
# tks = gpd.read_file(tks_bounds_p)
# tks = tks[tks['obs_year']==2015]

# if tks.crs != seg.crs:
#     tks = tks.to_crs(seg.crs)

## Select only those features within segmentation bounds
# xmin, ymin, xmax, ymax = seg.total_bounds
# tks = tks.cx[xmin:xmax, ymin:ymax]

# seg_cols = list(seg)
# seg_cols.append('tks_seg')
# seg['poly_geom'] = seg.geometry
# seg.geometry = seg.geometry.centroid
# # Locate segments whose centroids are within the tks boundary
# seg['tks_seg'] = seg.geometry.apply(lambda x: any([tk.contains(x) for tk in tks.geometry]))
# seg.geometry = seg['poly_geom']


# plt.style.use('ggplot')
# fig, ax = plt.subplots(1,1)
# seg.plot(column='tks_seg', alpha=0.75, ax=ax, cmap='bwr')
# seg.plot(facecolor='none', linewidth=0.5, ax=ax, edgecolor='white')
# tks.plot(facecolor='none', edgecolor='r', linewidth=1, ax=ax)
# plt.tight_layout()

# hfig, hax = plt.subplots(2,3, figsize=(14, 7))
# plot_cols = ['tpi31_mean', 'tpi41_mean',
#               'tpi81_mean', 'slope_mean',
#               'diff_mean', 'diffndvi_mean']

# hax = hax.flatten()
# for i, pc in enumerate(plot_cols):
#     ax = hax[i]
#     seg.hist(column=pc, ax=ax, edgecolor='w', bins=30)
#     ax.set_title(pc)
#     ax.axvline(seg[seg['tks_seg']==True][pc].mean(), color='black')
#     ax.set_yscale('log')
# plt.tight_layout()