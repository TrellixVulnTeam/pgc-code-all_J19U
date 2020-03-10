# -*- coding: utf-8 -*-
"""
Select stereo-pairs based on given parameters, including an AOI, date range, months, etc.
"""

import argparse
import logging.config
import os
import platform
import sys

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import write_ids, write_stereopair_ids
from misc_utils.logging_utils import LOGGING_CONFIG


def dem_selector(AOI_PATH, 
                 COORDS=None,
                 MONTHS=None, 
                 MIN_DATE=None, MAX_DATE=None,
                 MULTISPEC=False, 
                 OUT_STEREO_FP=None,
                 OUT_ID_LIST=None,
                 CLOUDCOVER=None):
    """
    Select stereopairs over an AOI, either from a passed DEM_FP, or from
    the danco database.

    Parameters
    ----------
    AOI_PATH : os.path.abspath
        Path to AOI shapefile.
    COORDS : LIST
        xy coordinates in WGS84 to use for selection.
    MONTHS : LIST, optional
        List of month integers to include. The default is None.
    MIN_DATE : STR, optional
        Minimum DEM date to include. E.g '2015-01-30'. The default is None.
    MAX_DATE : STR, optional
        Maximum DEM date to include. The default is None.
    MULTISPEC : BOOL, optional
        True to only select stereo from multispectral sources. The default is False.
    CLOUDCOVER : INT
        Only include pairs with cloudcover below this threshold
    OUT_STEREO_FP : os.path.abspath, optional
        Path to write DEM footprints shapefile to. The default is None.
    OUT_ID_LIST : os.path.abspath, optional
        Path to write catalogids of selected stereopair catalogids to. The default is None.

    Returns
    -------
    geopandas.GeoDataFrame : Dataframe of footprints matching selection.

    """
    #### PARAMETERS ####
    STEREO_FP = 'dg_imagery_index_stereo' # stereo footprint tablename
    CATALOGID = 'catalogid' # field name in danco footprint for catalogids
    DATE_COL = 'acqdate' # name of date field in stereo footprint
    SENSOR_COL = 'platform' # name of sensor field in stereo footprint
    PAIRNAME_COL = 'pairname' # name of field with unique pairnames
    CLOUDCOVER_COL = 'cloudcover' # name of field with cloudcover
    STEREOPAIR_ID = 'stereopair' # name of field with stereopair catalogid
    
    MONTH_COL = 'month' # name of field to create in footprint if months are requested 
    
    
    #### SETUP ####
    def check_where(where):
        """Checks if the input string exists already,
           if so formats correctly for adding to SQL"""
        if where:
            where += ' AND '
        return where
    
    
    # Create logger
    logging.config.dictConfig(LOGGING_CONFIG('DEBUG'))
    logger = logging.getLogger(__name__)
    

    #### LOAD INPUTS ####
    # Load AOI
    logger.info('Reading AOI...')
    if AOI_PATH:
        aoi = gpd.read_file(AOI_PATH)
    elif COORDS:
        lon = float(COORDS[0])
        lat = float(COORDS[1])
        loc = Point(lon, lat)
        aoi = gpd.GeoDataFrame(geometry=[loc], crs="EPSG:4326")


    # Load stereopairs footprint
    # Get bounds of aoi to reduce query size, with padding
    minx, miny, maxx, maxy = aoi.total_bounds
    pad = 10
    # Get DEM footprint crs - this loads no records, but it
    # will allow getting the crs of the footprints
    stereo = query_footprint(STEREO_FP, where="1=2")
    # Load stereo
    # Build SQL clause to select stereo in the area of the AOI, helps with load times
    stereo_where = """x1 > {} AND x1 < {} AND 
                      y1 > {} AND y1 < {}""".format(minx-pad, maxx+pad, 
                                                    miny-pad, maxy+pad)
    # Add date constraints to SQL
    if MIN_DATE:
        stereo_where = check_where(stereo_where)
        stereo_where += """{} > '{}'""".format(DATE_COL, MIN_DATE)
    if MAX_DATE:
        stereo_where = check_where(stereo_where)
        stereo_where += """{} < '{}'""".format(DATE_COL, MAX_DATE)
    # Add to SQL clause to just select multispectral sensors
    if MULTISPEC:
        stereo_where = check_where(stereo_where)
        stereo_where += """{} IN ('WV02', 'WV03')""".format(SENSOR_COL)
    if CLOUDCOVER:
        stereo_where = check_where(stereo_where)
        stereo_where += """{} <= {}""".format(CLOUDCOVER_COL, CLOUDCOVER)
    
    # Load DEM footprints with SQL
    stereo = query_footprint(STEREO_FP, where=stereo_where)
    
    # If only certain months requested, reduce to those
    if MONTHS:
        stereo['temp_date'] = pd.to_datetime(stereo[DATE_COL])
        stereo[MONTH_COL] = stereo['temp_date'].dt.month
        stereo.drop(columns=['temp_date'], inplace=True)
        stereo = stereo[stereo[MONTH_COL].isin(MONTHS)]

    logger.info('Stereopairs matching criteria (before AOI selection): {}'.format(len(stereo)))

    # Check coordinate system match and if not reproject AOI
    if aoi.crs != stereo.crs:
        aoi = aoi.to_crs(stereo.crs)
    
    
    #### SELECT stereo OVER ALL AOIS ####
    logger.info('Selecting stereopairs over AOI...')
    # Select by location
    # stereo = gpd.overlay(stereo, aoi, how='intersection')
    stereo = gpd.sjoin(stereo, aoi, how='inner')
    # Remove duplicates resulting from intersection (not sure why DUPs)
    stereo = stereo.drop_duplicates(subset=(PAIRNAME_COL))
    logger.info('Stereopairs found over AOI: {}'.format(len(stereo)))
    if len(stereo) == 0:
        logger.error('No stereopairss found over AOI, exiting...')
        sys.exit()
    
    
    #### WRITE FOOTPRINT AND TXT OF MATCHES ####
    # Write footprint out
    if OUT_STEREO_FP:
        logger.info('Writing stereopair footprint to file: {}'.format(OUT_STEREO_FP))
        stereo.to_file(OUT_STEREO_FP)
    # Write list of IDs ou
    if OUT_ID_LIST:
        logger.info('Writing list of catalogids to file: {}'.format(OUT_ID_LIST))
        write_stereopair_ids(list(stereo[CATALOGID]), list(stereo[STEREOPAIR_ID]), 
                             header='catalogid, stereopair',
                             out_path=OUT_ID_LIST)
    
    
    #### Summary Statistics ####
    count = len(stereo)
    min_date = stereo[DATE_COL].min()
    max_date = stereo[DATE_COL].max()
    
    logger.info("SUMMARY of STEREOPAIR SELECTION:")
    logger.info("Number of STEREOPAIRS: {}".format(count))
    logger.info("Earliest date: {}".format(min_date))
    logger.info("Latest date: {}".format(max_date))

    return stereo


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--aoi_path', type=os.path.abspath,
                        help='Path to AOI to select stereo over.')
    parser.add_argument('--coords', nargs='+',
                        help='Coordinates to use rather than AOI shapefile. Lon Lat')
    parser.add_argument('--out_stereo_footprint', type=os.path.abspath,
                        help="Path to write shapefile of selected stereopairs.")
    parser.add_argument('--out_id_list', type=os.path.abspath,
                        help="Path to write text file of selected stereopair's catalogids.")
    parser.add_argument('--months', nargs='+',
                        help='Months to include in selection, as intergers.')
    parser.add_argument('--min_date', type=str,
                        help='Minimum DEM date.')
    parser.add_argument('--max_date', type=str,
                        help='Maximum DEM date.')
    parser.add_argument('-ms', '--multispectral', action='store_true',
                        help='Use to select only stereo from multispectral sources.')
    parser.add_argument('-cc', '--cloudcover', type=int,
                    help='Maximum cloudcover to include.')
    
    args = parser.parse_args()
    
    AOI_PATH = args.aoi_path
    COORDS = args.coords
    OUT_STEREO_FP = args.out_stereo_footprint
    OUT_ID_LIST = args.out_id_list
    MONTHS = args.months
    MIN_DATE = args.min_date
    MAX_DATE = args.max_date
    MULTISPEC = args.multispectral
    CLOUDCOVER = args.cloudcover    
    
    dem_selector(AOI_PATH=AOI_PATH,
                 COORDS=COORDS,
                 OUT_STEREO_FP=OUT_STEREO_FP,
                 OUT_ID_LIST=OUT_ID_LIST,
                 MONTHS=MONTHS,
                 MIN_DATE=MIN_DATE,
                 MAX_DATE=MAX_DATE,
                 MULTISPEC=MULTISPEC,
                 CLOUDCOVER=CLOUDCOVER)
