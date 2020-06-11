# -*- coding: utf-8 -*-
"""
Created on Tue May 21 11:25:36 2019

@author: disbr007

Get percentage overlap for each footprint over *single* AOI polygon
"""
import argparse
import os

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def determine_overlap(aoi_path, index_path, out_path, percent_ovlp, max_cloudcover):
    """Add column containing overlap of each feature in index with aoi_path, as percentage"""
    # Global parameters
    # Path and names
    # project_path = os.path.dirname(aoi_path)
    # aoi_name = os.path.basename(aoi_path).split('.')[0]
    # out_path = os.path.join(project_path, '{}_ovlp.shp'.format(aoi_name))

    # Open AOI layer, deal with projection
    # Get total area of AOI
    aoi = gpd.read_file(aoi_path)
    aoi_feat = aoi[0:]
    aoi_area = aoi_feat.geometry.area[0]

    # Open footprints layer
    idx = gpd.read_file(index_path)
    if max_cloudcover:
        idx = idx[idx.CLOUDCOVER <= max_cloudcover]

    # Ensure projections match - if not reproject
    if aoi.crs != idx.crs:
        logger.debug('Reprojecting index to match aoi crs: {}'.format(aoi.crs))
        idx = idx.to_crs(aoi.crs)

    # Calculate area of overlap with AOI for each footprint, save to new field
    # Set index name for joining later
    iname = 'idx_index'
    idx.index = pd.RangeIndex(start=1, stop=len(idx.index)+1)
    idx.index.name = iname
    idx.reset_index(inplace=True)
    # Get all intersections
    intersections = gpd.overlay(idx, aoi, how='intersection')

    # Determine overlap percentage
    intersections['ovlp_perc'] = (intersections.geometry.area / aoi_area).round(decimals=2) * 100

    # Join back to oringal footprint geometries
    idx = pd.merge(idx, intersections[[iname, 'ovlp_perc']], on=iname)

    # Limit to minimum percent overlap, if specified
    if percent_ovlp:
        idx = idx[idx.ovlp_perc >= percent_ovlp]

    logger.info('Maximum overlap: {}%'.format(max(idx['ovlp_perc'])))
    logger.info('Minimum overlap: {}%'.format(min(idx['ovlp_perc'])))

    # Write footprint to new file with overlap percentage column
    idx.reset_index(inplace=True)
    logger.info('Writing to: {}'.format(out_path))
    idx.to_file(out_path)

    return idx


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('aoi', type=os.path.abspath, help='Shapefile of area of interest.')
    parser.add_argument('footprint_layer', type=os.path.abspath, help='Footprint shapefile to use.')
    parser.add_argument('out_path', type=os.path.abspath, help='Path to write shapefile with overlap percentage to.')
    parser.add_argument('-p', '--percent_overlap', dest="percent_overlap", default=None, type=float, help='Minimum percentage overlap to write. e.g.: 50')
    parser.add_argument('-c', '--max_cloudcover', dest='max_cloudcover', default=None, type=float, help='Max cloudcover. e.g.: 0.20')
    args = parser.parse_args()

    aoi_path = args.aoi
    fp_lyr_path = args.footprint_layer
    out_path = args.out_path
    percent_ovlp = args.percent_overlap
    max_cloudcover = args.max_cloudcover

    determine_overlap(aoi_path, fp_lyr_path, out_path, percent_ovlp, max_cloudcover)
