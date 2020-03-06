# -*- coding: utf-8 -*-
"""
Select DEMs based on given parameters, including an AOI, date range, months, etc.
"""

import argparse
import logging.config
import os
import platform

import pandas as pd
import geopandas as gpd
from tqdm import tqdm

from dem_utils.valid_data import valid_percent_clip
from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import write_ids
from misc_utils.logging_utils import LOGGING_CONFIG


# TODO: speed up by reprojecting once when warping/checking valid percentage (workaround impl.)
# TODO: change writing of dem FP with valid percents to actual location, not scratch
# TODO: Double check duplicate DEMS for each AOI


#### INPUTS ####
# # Optional
# AOI_PATH = r'E:/disbr007/umn/ms/shapefile/aois/pot_aois/aoi6_2020feb01.shp'
# DEM_FP = r'E:\disbr007\umn\ms\shapefile\dem_footprints\banks_multispec_lewk_vp_ms_6_7_8_9_vp50.shp'

# MONTHS = [6, 7, 8, 9]
# MIN_DATE = ''
# MAX_DATE = ''
# MULTISPEC = True
# DENSITY_THRESH = None # 

# PRJ_DIR = r'E:\disbr007\umn\ms' # project directory
# OUT_DEM_DIR = None
# DEM_SUB = 'dems' # default DEM subdirectory name, if not provided

# # File name of footprint of clipped DEMs
# DEM_FP_OUTPATH = None
# OUT_ID_LIST = None


def dem_selector(AOI_PATH, 
                 COORDS=None,
                 DEM_FP=None,
                 MONTHS=None, 
                 MIN_DATE=None, MAX_DATE=None,
                 MULTISPEC=False, 
                 DENSITY_THRESH=None,
                 VALID_THRESH=None,
                 OUT_DEM_FP=None,
                 OUT_ID_LIST=None):
    """
    Select DEMs over an AOI, either from a passed DEM_FP, or from
    the danco database.

    Parameters
    ----------
    AOI_PATH : os.path.abspath
        Path to AOI shapefile.
    DEM_FP : os.path.abspath, optional
        Path to a footprint of DEMs. The default is None.
    MONTHS : LIST, optional
        List of month integers to include. The default is None.
    MIN_DATE : STR, optional
        Minimum DEM date to include. E.g '2015-01-30'. The default is None.
    MAX_DATE : STR, optional
        Maximum DEM date to include. The default is None.
    MULTISPEC : BOOL, optional
        True to only select DEMs from multispectral sources. The default is False.
    DENSITY_THRESH : FLOAT, optional
        Minimum density value to keep. The default is None.
    DEM_FP_OUTPATH : os.path.abspath, optional
        Path to write DEM footprints shapefile to. The default is None.
    OUT_ID_LIST : os.path.abspath, optional
        Path to write catalogids of selected DEMs to. Only one per DEM. The default is None.

    Returns
    -------
    geopandas.GeoDataFrame : Dataframe of footprints matching selection.

    """
    #### PARAMETERS ####
    WINDOWS_OS = 'Windows' # value returned by platform.system() for windows
    LINUX_OS = 'Linux' # value return by platform.system() for linux
    WINDOWS_LOC = 'win_path' # field name of windows path in footprint
    LINUX_LOC = 'filepath' # linux path field
    DEM_FNAME = 'dem_name' # field name with filenames (with ext)
    DEMS_FP = 'pgc_dem_setsm_strips' # Danco DEM footprint tablename
    CATALOGID = 'catalogid1' # field name in danco DEM footprint for catalogids
    DATE_COL = 'acqdate1' # name of date field in dems footprint
    DENSITY_COL = 'density' # name of density field in dems footprint
    SENSOR_COL = 'sensor1' # name of sensor field in dems footprint
    
    FULLPATH = 'fullpath' # created field name in footprint with path to files
    VALID_PERC = 'valid_perc' # created field name in footprint to store valid %
    MONTH_COL = 'month' # name of field to create in dems footprint if months are requested 
    
    
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
        aoi = gpd.GeoDataFrame(geometry=[Point(coords[0], coords[1])], crs="EPSG:4326")
    
    # If DEM footprint provided, use that, else use danco with parameters
    if DEM_FP:
        logger.info('Reading provided DEM footprint...')
        dems = gpd.read_file(DEM_FP)
        if MIN_DATE:
            dems = dems[dems[DATE_COL] > MIN_DATE]
        if MAX_DATE:
            dems = dems[dems[DATE_COL] < MAX_DATE]
        if MULTISPEC:
            dems = dems[dems[SENSOR_COL].isin(['WV02', 'WV03'])]
        if DENSITY_THRESH:
            dems = dems[dems[DENSITY_COL] > DENSITY_THRESH]
    else:
        # Get bounds of aoi to reduce query size, with padding
        minx, miny, maxx, maxy = aoi.total_bounds
        pad = 10
        # Get DEM footprint crs - this loads no records, but it
        # will allow getting the crs of the footprints
        dems = query_footprint(DEMS_FP, where="1=2")
        # Load DEMs
        # Build SQL clause to select DEMs in the area of the AOI, helps with load times
        dems_where = """cent_lon > {} AND cent_lon < {} AND 
                        cent_lat > {} AND cent_lat < {}""".format(minx-pad, maxx+pad, miny-pad, maxy+pad)
        # Add date constraints to SQL
        if MIN_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} > '{}'""".format(DATE_COL, MIN_DATE)
        if MAX_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} < '{}'""".format(DATE_COL, MAX_DATE)
        # Add to SQL clause to just select multispectral sensors
        if MULTISPEC:
            dems_where = check_where(dems_where)
            dems_where += """{} IN ('WV02', 'WV03')""".format(SENSOR_COL)
        # Add density threshold to SQL
        if DENSITY_THRESH:
            dems_where = check_where(dems_where)
            dems_where += """{} > {}""".format(DENSITY_COL, DENSITY_THRESH)
        # Load DEM footprints with SQL
        dems = query_footprint(DEMS_FP, where=dems_where)
    
    # If only certain months requested, reduce to those
    if MONTHS:
        dems['temp_date'] = pd.to_datetime(dems[DATE_COL])
        dems[MONTH_COL] = dems['temp_date'].dt.month
        dems.drop(columns=['temp_date'], inplace=True)
        dems = dems[dems[MONTH_COL].isin(MONTHS)]
    
    # Check coordinate system match and if not reproject AOI
    if aoi.crs != dems.crs:
        aoi = aoi.to_crs(dems.crs)
 
    
    #### SELECT DEMS OVER ALL AOIS ####
    logger.info('Selecting DEMs over AOI...')
    # Select by location
    dems = gpd.overlay(dems, aoi, how='intersection')
    # Remove duplicates resulting from intersection (not sure why DUPs)
    dems = dems.drop_duplicates(subset=(DEM_FNAME))
    logger.info('DEMs found over AOI: {}'.format(len(dems)))
    
    # Create full path to server location, used or checking validity
    # Determine operating system for locating DEMs
    OS = platform.system()
    if OS == WINDOWS_OS:
        server_loc = WINDOWS_LOC
    elif OS == LINUX_OS:
        server_loc = LINUX_LOC    
    dems[FULLPATH] = dems.apply(lambda x: os.path.join(x[server_loc], x[DEM_FNAME]), axis=1)
    # Subset to only those DEMs that actually can be found
    dems = dems[dems[FULLPATH].apply(lambda x: os.path.exists(x))==True]
    
    
    #### GET VALID DATA PERCENT ####
    if VALID_THRESH:
        logger.info('Determining percent of non-NoData pixels over AOI for each DEM...')
        # dems[VALID_PERC] = dems.apply(lambda x: valid_percent_clip(AOI_PATH, x[FULLPATH]), axis=1)
        
        dems[VALID_PERC] = -9999
        for row in tqdm(dems[[FULLPATH, VALID_PERC]].itertuples(index=True),
                        total=len(dems)):
            # print(row)
            # print(row[0])
            # print(row[1])
            vp = valid_percent_clip(AOI_PATH, row[1]) # Index is row[0], then passed columns
            dems.at[row.Index, VALID_PERC] = vp
    
        dems = dems[dems[VALID_PERC] > VALID_THRESH]
            
    #### WRITE FOOTPRINT AND TXT OF MATCHES ####
    # Write footprint out
    if OUT_DEM_FP:
        logger.info('Writing DEMs footprint to file: {}'.format(OUT_DEM_FP))
        dems.to_file(OUT_DEM_FP)
    # Write list of IDs ou
    if OUT_ID_LIST:
        logger.info('Writing list of DEM catalogids to file: {}'.format(OUT_ID_LIST))
        write_ids(list(dems[CATALOGID]), OUT_ID_LIST)
    
    
    #### Summary Statistics ####
    count = len(dems)
    min_date = dems[DATE_COL].min()
    max_date = dems[DATE_COL].max()
    min_density = dems[DENSITY_COL].min()
    max_density = dems[DENSITY_COL].max()
    avg_density = dems[DENSITY_COL].mean()
    if VALID_THRESH:
        min_valid = dems[VALID_PERC].min()
        max_valid = dems[VALID_PERC].max()
        avg_valid = dems[VALID_PERC].mean()
        
    
    logger.info("SUMMARY of DEM SELECTION:")
    logger.info("Number of DEMs: {}".format(count))
    logger.info("Earliest date: {}".format(min_date))
    logger.info("Latest date: {}".format(max_date))
    logger.info("Minimum density: {:.2}".format(min_density))
    logger.info("Maximum density: {:.2}".format(max_density))
    logger.info("Average density: {:.2}".format(avg_density))
    if VALID_THRESH:
        logger.info('Minimum valid percentage over AOI: {}'.format(min_valid))
        logger.info('Maximum valid percentage over AOI: {}'.format(max_valid))
        logger.info('Average valid percentage over AOI: {}'.format(avg_valid))
    
    return dems


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--aoi_path', type=os.path.abspath,
                        help='Path to AOI to select DEMs over.')
    parser.add_argument('--coords', nargs='+',
                        help='Coordinates to use rather than AOI shapefile.')
    parser.add_argument('--out_dem_footprint', type=os.path.abspath,
                        help="Path to write shapefile of selected DEMs.")
    parser.add_argument('--out_id_list', type=os.path.abspath,
                        help="Path to write text file of selected DEM's catalogids.")
    parser.add_argument('--dems_footprint', type=os.path.abspath,
                        help='Path to DEM footprints')
    parser.add_argument('--months', nargs='+',
                        help='Months to include in selection, as intergers.')
    parser.add_argument('--min_date', type=str,
                        help='Minimum DEM date.')
    parser.add_argument('--max_date', type=str,
                        help='Maximum DEM date.')
    parser.add_argument('-ms', '--multispectral', action='store_true',
                        help='Use to select only DEMs from multispectral sources.')
    parser.add_argument('--density_threshold', type=float,
                        help='Minimum density to include in selection.')
    parser.add_argument('--valid_aoi_threshold', type=float,
                        help="""Threshold percent of non-Nodata pixels over AOI for each DEM.
                                Not recommended for large selections.""")
    
    args = parser.parse_args()
    
    AOI_PATH = args.aoi_path
    COORDS = args.coords
    OUT_DEM_FP = args.out_dem_footprint
    OUT_ID_LIST = args.out_id_list
    DEM_FP = args.dems_footprint
    MONTHS = args.months
    MIN_DATE = args.min_date
    MAX_DATE = args.max_date
    MULTISPEC = args.multispectral
    DENSITY_THRESH = args.density_threshold
    VALID_THRESH = args.valid_aoi_threshold
    
    
    dem_selector(AOI_PATH=AOI_PATH,
                 OUT_DEM_FP=OUT_DEM_FP,
                 OUT_ID_LIST=OUT_ID_LIST,
                 DEM_FP=DEM_FP,
                 MONTHS=MONTHS,
                 MIN_DATE=MIN_DATE,
                 MAX_DATE=MAX_DATE,
                 MULTISPEC=MULTISPEC,
                 DENSITY_THRESH=DENSITY_THRESH,
                 VALID_THRESH=VALID_THRESH)