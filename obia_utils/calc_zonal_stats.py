# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 14:00:03 2020

@author: disbr007
"""

import logging.config
import os
# import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import geopandas as gpd
# import fiona
# import rasterio
from rasterstats import zonal_stats

from misc_utils.logging_utils import LOGGING_CONFIG


logging.config.dictConfig(LOGGING_CONFIG('INFO'))
logger = logging.getLogger(__name__)


# Inputs
seg_path = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_clip_ms_lsms_sr5rr200ss150.shp'
tpi31_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\tpi\WV02_20150906_tpi31.tif'
tpi41_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\tpi\WV02_20150906_tpi41.tif'
slope_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\slope\WV02_20150906_pcatdmx_slope.tif'
diff_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\dems\diffs\WV02_20150906_WV02_20130711_diff.tif'
ndvi_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\imagery\ndvi_ps\WV02_20150906203203_1030010048B0FA00_15SEP06203203-M1BS-500447187090_01_P008_u16mr3413_pansh_ndvi.tif'
diff_ndvi_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\imagery\diff_ndvi_ps\diff_ndvi_ps_WV02_20150906_WV02_20130711.tif'

tks_bounds_p = r'E:\disbr007\umn\ms\shapefile\tk_loc\digitized_thaw_slumps.shp'

outpath = os.path.join(os.path.dirname(seg_path),
                       '{}_stats.shp'.format(os.path.basename(seg_path).split('.')[0]))


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

# tpi_stats = {'mean': 'tpi_mean', 
#               'min': 'tpi_min', 
#               'max': 'tpi_max',
#               'std': 'tpi_std'}

slope_stats = {'mean': 'slope_mean', 
                'max': 'slope_max',
                'std': 'slope_std'}

diff_stats = {'mean': 'diff_mean',
              'max': 'diff_max',
              'min': 'diff_min'}

diff_ndvi_stats = {'mean': 'diffndvi_mean',
              'min': 'diffndvi_min',
              'max': 'diffndvi_max'}

stats_on = [(tpi31_path, tpi31_stats), 
            (tpi41_path, tpi41_stats),
            (slope_path, slope_stats),
            (diff_path, diff_stats),
            (diff_ndvi_path, diff_ndvi_stats)]

for raster, stats in stats_on:
    seg = compute_stats(seg, raster, stats)
logger.info('Zonal statistics computed.')

#### Compute geometric statistics
# Area
seg['area_m'] = seg.geometry.area
# Compactness: Polsby-Popper Score -- 1 = circle
seg['compact'] = (np.pi * 4 * seg.geometry.area) / (seg.geometry.boundary.length)**2


# Write segments with stats to new shapefile
logger.info('Writing segments with statsitics')
seg.to_file(outpath)
logger.info('Done.')

## Find segments in predrawn thermokarst boundaries
tks = gpd.read_file(tks_bounds_p)
tks = tks[tks['obs_year'] == 2015]

if tks.crs != seg.crs:
    tks = tks.to_crs(seg.crs)
    
# x = gpd.sjoin(gdf, tks, how='left', op='within')
# x['tks'] = np.logical_not(x['index_right'].isna())



# fig, ax = plt.subplots(1,1)
# seg.plot(column='tpi_mean', ax=ax, legend=True)
# x.plot(column='tks', ax=ax)
# tks.plot(facecolor='none', edgecolor='r', ax=ax)
# plt.tight_layout()


