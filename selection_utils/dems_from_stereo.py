# -*- coding: utf-8 -*-
"""
Created on Tue May 19 10:49:25 2020

@author: disbr007
"""
import argparse
import glob
import os
import platform

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from dem_utils.copy_dems import copy_dems
from selection_utils.query_danco import query_footprint, layer_crs
from misc_utils.logging_utils import create_logger


def check_where(where, op='AND'):
        """Checks if the input string exists already,
           if so formats correctly for adding to SQL"""
        if where:
            where += ' {} '.format(op)
        return where
    

def loc_pairname_dems(basepath, region_id, pairname, strip_types=['strips', 'strips_v4']):
        all_dems = []
        for strips in strip_types:
            
            dems_pattern = os.path.join(basepath, region_id, '{}'.format(strips), '2m', 
                                        '{}*'.format(pairname), '{}*dem.tif'.format(pairname))
            dems = glob.glob(dems_pattern)
            if dems:
                all_dems.extend(dems)
            
        dems_df = pd.DataFrame({'pairname': [pairname for i in range(len(all_dems))], 
                                dem_path:  [d for d in all_dems]})
        
        return dems_df
    
    
def dems_from_stereo(aoi_path=None,
                     coords=None,
                     months=None,
                     min_date=None, max_date=None,
                     multispec=False,
                     dem_path='dem_path',
                     strip_types=['strips, strips_v4']):

    # Params
    stereo_lyr_name = 'dg_imagery_index_stereo_with_earthdem_region'
    DATE_COL = 'acqdate' # name of date field in stereo footprint
    SENSOR_COL = 'platform' # name of sensor field in stereo footprint
    
    if aoi_path or coords:
        if aoi_path:
            # Load AOI
            aoi = gpd.read_file(aoi_path)
            # Check AOI crs
            stereo_crs = layer_crs(stereo_lyr_name)
            if aoi.crs != stereo_crs:
                logger.debug('Reprojecting AOI to match footprint: AOI -> {}'.format(stereo_crs))
                aoi = aoi.to_crs(stereo_crs)
        elif coords:
            lon = float(coords[0])
            lat = float(coords[1])
            loc = Point(lon, lat)
            aoi = gpd.GeoDataFrame(geometry=[loc], crs="EPSG:4326")
    
        # Get AOI bounds
        minx, miny, maxx, maxy = aoi.total_bounds
        pad = 3
        where = "x1 > {} AND y1 > {} AND x1 < {} and y1 < {}".format(minx-pad, miny-pad, maxx+pad, maxy+pad)
    
    # Add constraints to SQL
    if min_date:
        where = check_where(where)
        where += """{} > '{}'""".format(DATE_COL, min_date)
    if max_date:
        where = check_where(where)
        where += """{} < '{}'""".format(DATE_COL, max_date)
    # Add to SQL clause to just select multispectral sensors
    if multispec:
        where = check_where(where)
        where += """{} IN ('WV02', 'WV03')""".format(SENSOR_COL)
    if months:
        month_terms = [""" {} LIKE '%%-{}-%%'""".format(DATE_COL, month) for month in months]
        month_sql = " OR ".join(month_terms)
        month_sql = "({})".format(month_sql)
        where = check_where(where)
        where += month_sql

    # Load stereo footprint
    logger.info('Loading stereo footprint...')
    logger.debug('SQL where: {}'.format(where))
    stereo = query_footprint(stereo_lyr_name, where=where, dryrun=False)
    logger.debug('Initial matches with SQL: {}'.format(len(stereo)))

    # Intersect with AOI
    logger.info('Finding footprints that intersect with AOI...')
    stereo_matches = gpd.overlay(stereo, aoi)
    logger.debug('Matches with AOI intersection: {}'.format(len(stereo_matches)))

    # Create paths
    if platform.system() == 'Windows':
        basepath = r'V:\pgc\data\elev\dem\setsm\ArcticDEM\region'
    elif platform.syystem() == 'Linux':
        basepath = r'/mnt/pgc/data/elev/dem/setsm/ArcticDEM/region'

    # Look for DEM paths for all pairnames
    pairname_paths = pd.DataFrame()
    for i, row in stereo_matches.iterrows():
        pairname_dems = loc_pairname_dems(basepath, row['region_id'], row['pairname'], strip_types=)
        pairname_paths = pd.concat([pairname_paths, pairname_dems])

    # Join back to matches, one row per DEM found per pairname
    # or if no DEM found for pairname, a single row with dem_path=NaN
    matches_paths = pd.merge(stereo_matches, pairname_paths, how='outer',
                             left_on='pairname', right_on='pairname')

    # Split into found and missing dems, report
    found_dems = matches_paths[~matches_paths[dem_path].isna()]
    missing_dems = matches_paths[matches_paths[dem_path].isna()]

    logger.info('Found pairnames: {}/{}'.format(len(found_dems['pairname'].unique()),
                                                len(stereo_matches)))
    logger.info('Found DEMs: {}'.format(len(found_dems)))

    if not found_dems.empty:
        logger.debug('Found DEMs summary: ')
        logger.debug('Total:       {}'.format(len(found_dems)))
        logger.debug('Min acqdate: {}'.format(found_dems['acqdate'].min()))
        logger.debug('Max acqdate: {}'.format(found_dems['acqdate'].max()))
        logger.debug('Sensors:     {}'.format(sorted(found_dems['platform'].unique())))
        logger.debug('Found DEMs:\n{}'.format(found_dems['pairname']))
        logger.debug('')
    if not missing_dems.empty:
        logger.debug('Missing DEMs summary: ')
        logger.debug('Total:        {}'.format(len(missing_dems)))
        logger.debug('Min acqdate:  {}'.format(missing_dems['acqdate'].min()))
        logger.debug('Max acqdate:  {}'.format(missing_dems['acqdate'].max()))
        logger.debug('Sensors:      {}'.format(sorted(missing_dems['platform'].unique())))
        logger.debug('Missing DEMs:\n{}'.format(missing_dems['pairname']))

    return found_dems


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-ap', '--aoi_path', type=os.path.abspath,
                        help='Path to AOI to use to select footprints.')
    parser.add_argument('--coords', nargs='+',
                        help='Coordinates to use rather than AOI shapefile. Lon Lat')
    parser.add_argument('--v4_only', action='store_true',
                        help='Select DEMs only from strips_v4 subdirectories.')
    parser.add_argument('--months', nargs='+',
                        help='Months to include in selection, as intergers.')
    parser.add_argument('--min_date', type=str,
                        help='Minimum DEM date.')
    parser.add_argument('--max_date', type=str,
                        help='Maximum DEM date.')
    parser.add_argument('-ms', '--multispectral', action='store_true',
                        help='Use to select only DEMs from multispectral sources.')
    parser.add_argument('--out_dem_footprint', type=os.path.abspath,
                        help="Path to write shapefile of selected DEMs.")
    parser.add_argument('--out_filepaths', type=os.path.abspath,
                        help="Path to write text file of DEM's full paths.")
    parser.add_argument('--copy_to', type=os.path.abspath,
                        help='Path to copy DEMs to.')
    parser.add_argument('-do', '--dems_only', action='store_true',
                        help='Use to only copy dem.tif files.')
    parser.add_argument('-so', '--skip_ortho', action='store_true',
                        help='Use to skip ortho files, but copy all other meta files.')
    parser.add_argument('-f', '--flat', action='store_true',
                        help='Use to not create DEM subdirectories, just copy to destination directory.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging to DEBUG')
    parser.add_argument('-dr', '--dryrun', action='store_true',
                        help='Use to check for DEMs existence but do not copy.')

    args = parser.parse_args()

    aoi_path = args.aoi_path
    coords = args.coords
    v4_only = args.v4_only
    months = args.months
    min_date = args.min_date
    max_date = args.max_date
    multispec = args.multispectral
    out_filepaths = args.out_filepaths
    out_dem_fp = args.out_dem_footprint
    copy_to = args.copy_to
    dems_only = args.dems_only
    skip_ortho = args.skip_ortho
    flat = args.flat
    dryrun = args.dryrun
    verbose = args.verbose

    if verbose:
        log_lvl = 'DEBUG'
    else:
        log_lvl = 'INFO'
    logger = create_logger(__name__, 'sh', log_lvl)

    # Param
    dem_path = 'dem_path'
    if v4_only:
        strip_types = ['strips_v4']
    else:
        strip_types = ['strips', 'strips_v4']

    # Locate DEMs that match
    logger.info('Locating matching DEMs...')
    dems = dems_from_stereo(aoi_path=aoi_path,
                            coords=coords,
                            strip_types=strip_types,
                            months=months,
                            min_date=min_date,
                            max_date=max_date,
                            multispec=multispec,
                            dem_path=dem_path)


    if out_filepaths:
        logger.info('Writing matching DEM paths to {}'.format(out_filepaths))
        if not dryrun:
            with open(out_filepaths, 'w') as src:
                for dem_fp in dems[dem_path].values:
                    src.write(dem_fp)
                    src.write('\n')

    if out_dem_fp:
        logger.info('Writing matching DEM fooprint to {}'.format(out_dem_fp))
        if not dryrun:
            dems.to_file(out_dem_fp)

    if copy_to:
        logger.info('Copying DEMs to: {}'.format(copy_to))
        copy_dems(dems, copy_to, dems_only=dems_only, skip_ortho=skip_ortho, flat=flat, dryrun=dryrun)

    logger.info('Done.')
