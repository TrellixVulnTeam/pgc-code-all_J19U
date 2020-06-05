# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 08:46:36 2019

@author: disbr007
"""

import argparse
import copy
import sys

import geopandas as gpd
# from osgeo import gdal

from archive_analysis.archive_analysis_utils import get_count
from misc_utils.logging_utils import create_logger
from selection_utils.query_danco import list_danco_db, query_footprint


logger = create_logger(__name__, 'sh', 'INFO')

def calculate_density(grid_p, footprint_p, out_path=None, date_col=None, rasterize=False):
    if not isinstance(grid_p, gpd.GeoDataFrame):
        logger.info('Loading grid...')
        if 'gdb' in grid_p:
            gdb, layer = grid_p.split('.gdb\\')
            gdb = '{}.gdb'.format(gdb)
            grid = gpd.read_file(gdb, layer=layer)
        else:
            grid = gpd.read_file(grid_p)
    else:
        grid = copy.deepcopy(grid_p)

    danco_footprints = list_danco_db('footprint')
    if isinstance(footprint_p, gpd.GeoDataFrame):
        footprint = copy.deepcopy(footprint_p)
    elif footprint_p in danco_footprints:
        logger.info('Loading footprint from danco...')
        footprint = query_footprint(footprint_p)
    else:
        logger.info('Loading footprint...')
        if 'gdb' in footprint_p:
            gdb, layer = footprint_p.split('.gdb\\')
            gdb = '{}.gdb'.format(gdb)
            footprint = gpd.read_file(gdb, layer=layer)
        else:
            footprint = gpd.read_file(footprint_p)


    logger.info('Calculating density...')
    density = get_count(grid, footprint, date_col=date_col)
    # Convert any tuple columns to strings (occurs with agg-ing same column multiple ways)
    density.columns = [str(x) if type(x) == tuple else x for x in density.columns]
    if rasterize:
        logger.info('Rasterizing...')
        vec_out = '/vsimem/density_temp.shp'
        density.to_file(vec_out)
        # TODO: Finish this
        # rasterize_options = gdal.RasterizeOptions(xRes=, yRes=, )
        if out_path:
            1 == 1
            # Rasterize to out_path
    else:
        if out_path:
            logger.info('Writing density...')
            density.to_file(out_path)
        
    return density


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('input_grid', type=str, help='Grid to count density on.')
    parser.add_argument('input_footprint', type=str, help='Footprint to calculate density of.')
    parser.add_argument('out_path', type=str, help='Path to write the density shapefile.')
    parser.add_argument('--date_col', type=str, help="""Column in input footprint holding dates
                                                        to return min and max dates""")
    parser.add_argument('-r', '--rasterize', action='store_true',
                        help="""Use this flag to rasterize the output. out_path must have a GDAL
                                writable extension.""")

    args = parser.parse_args()

    grid_p = args.input_grid
    footprint_p = args.input_footprint
    out_path = args.out_path
    date_col = args.date_col
    rasterize = args.rasterize
    
    calculate_density(grid_p=grid_p,
                      footprint_p=footprint_p,
                      out_path=out_path,
                      date_col=date_col,
                      rasterize=rasterize)
