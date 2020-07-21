# -*- coding: utf-8 -*-
"""
Select DEMs based on given parameters, including an AOI, date range, months, etc.
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

# from dem_utils.valid_data import valid_percent_clip
from valid_data import valid_percent_clip
from selection_utils.db_utils import Postgres, generate_sql, intersect_aoi_where
# from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import write_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')



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


def dem_selector(AOI_PATH=None, 
                 COORDS=None,
                 DEM_FP=None,
                 MONTHS=None, 
                 MIN_DATE=None, MAX_DATE=None,
                 DATE_COL=None,
                 MULTISPEC=False,
                 RES=None,
                 DENSITY_THRESH=None,
                 LOCATE_DEMS=False,
                 VALID_THRESH=None,
                 OUT_DEM_FP=None,
                 OUT_ID_LIST=None,
                 BOTH_IDS=False,
                 OUT_FILEPATH_LIST=None):
    """
    Select DEMs over an AOI, either from a passed DEM_FP, or from
    the danco database.

    Parameters
    ----------
    AOI_PATH : os.path.abspath
        Path to AOI shapefile.
    COORDS : tuple
        Lon, Lat to use instead of aoi.
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
    PAIRNAME = 'pairname'
    DEMS_DB = 'sandwich-pool.dem'  # Sandwich DEM database
    DEMS_FP =  'dem.scene_dem_master'  # Sandwich DEM footprint tablename
    DEMS_GEOM = 'wkb_geometry' # Sandwich DEMs geometry name
    CATALOGID1 = 'catalogid1' # field name in danco DEM footprint for catalogids
    CATALOGID2 = 'catalogid2'
    if not DATE_COL:
        DATE_COL = 'acqdate1' # name of date field in dems footprint
    DENSITY_COL = 'density' # name of density field in dems footprint
    SENSOR_COL = 'sensor1' # name of sensor field in dems footprint
    RES_COL = 'dem_res'
    FULLPATH = 'fullpath' # created field name in footprint with path to files
    VALID_PERC = 'valid_perc' # created field name in footprint to store valid %
    MONTH_COL = 'month' # name of field to create in dems footprint if months are requested 
    
    
    #### SETUP ####
    def check_where(where):
        """Checks if the input string exists already,
           if so formats correctly for adding to SQL
           WHERE clause"""
        if where:
            where += ' AND '
        return where
    

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
        # Get DEM footprint crs - this loads only one records, but it
        # will allow getting the crs of the footprints
        with Postgres(db_name=DEMS_DB) as dem_db:
            crs_sql = generate_sql(layer=DEMS_FP, geom_col='wkb_geometry', encode_geom_col='geom', limit=1)
            # logger.debug(crs_sql)
            dems = dem_db.sql2gdf(sql=crs_sql)
        # dems = query_footprint(DEMS_FP, limit=1)


        # minx, miny, maxx, maxy = aoi.total_bounds
        # pad = 10

        # Load DEMs
        # Build SQL clause to select DEMs in the area of the AOI, helps with load times
        # Reproject if necessary
        if aoi.crs != dems.crs:
            aoi = aoi.to_crs(dems.crs)
        # Create PostGIS intersection where clause
        dems_where = intersect_aoi_where(aoi=aoi, geom_col=DEMS_GEOM)

        # dems_where = """cent_lon > {} AND cent_lon < {} AND
        #                 cent_lat > {} AND cent_lat < {}""".format(minx-pad, maxx+pad, miny-pad, maxy+pad)
        # Add date constraints to SQL
        if MIN_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} > '{}'""".format(DATE_COL, MIN_DATE)
        if MAX_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} < '{}'""".format(DATE_COL, MAX_DATE)
        if RES:
            dems_where = check_where(dems_where)
            dems_where += """{} = {}""".format(RES_COL, RES)
        # Add to SQL clause to just select multispectral sensors
        if MULTISPEC:
            dems_where = check_where(dems_where)
            dems_where += """{} IN ('WV02', 'WV03')""".format(SENSOR_COL)
        # Add density threshold to SQL
        if DENSITY_THRESH:
            dems_where = check_where(dems_where)
            dems_where += """{} > {}""".format(DENSITY_COL, DENSITY_THRESH)

        # Load DEM footprints with SQL
        with Postgres(db_name=DEMS_DB) as dem_db:
            dems_sql = generate_sql(layer=DEMS_FP, where=dems_where)
            logger.debug(dems_sql)
            dems = dem_db.sql2gdf(sql=dems_sql, geom_col=DEMS_GEOM)
        # dems = query_footprint(DEMS_FP, where=dems_where)
    
    # If only certain months requested, reduce to those
    if MONTHS:
        dems['temp_date'] = pd.to_datetime(dems[DATE_COL])
        dems[MONTH_COL] = dems['temp_date'].dt.month
        dems.drop(columns=['temp_date'], inplace=True)
        dems = dems[dems[MONTH_COL].isin(MONTHS)]

    logger.info('DEMs matching criteria (before AOI selection): {}'.format(len(dems)))
    if len(dems) == 0:
        logger.warning('No matching DEMs found (before AOI selection).')
        sys.exit()

    # Check coordinate system match and if not reproject AOI
    # if aoi.crs != dems.crs:
    #     aoi = aoi.to_crs(dems.crs)


    #### SELECT DEMS OVER ALL AOIS ####
    # logger.info('Selecting DEMs over AOI...')
    # # Select by location
    # dem_cols = list(dems)
    # dems = gpd.sjoin(dems, aoi)
    # dems = dems[dem_cols]
    #
    # # Remove duplicates resulting from intersection (not sure why DUPs)
    # if DEM_FNAME not in list(dems):
    #     DEM_FNAME = PAIRNAME
    #
    # dems = dems.drop_duplicates(subset=(DEM_FNAME))
    logger.info('DEMs found over AOI: {:,}'.format(len(dems)))
    if len(dems) == 0:
        logger.error('No DEMs found over AOI, exiting...')
        sys.exit()
    
    # Create full path to server location, used for checking validity
    # Determine operating system for locating DEMs
    if LOCATE_DEMS:
        OS = platform.system()
        if OS == WINDOWS_OS:
            server_loc = WINDOWS_LOC
        elif OS == LINUX_OS:
            server_loc = LINUX_LOC
        dems[FULLPATH] = dems.apply(lambda x: os.path.join(x[server_loc], x[DEM_FNAME]), axis=1)
        # # Subset to only those DEMs that actually can be found
        # logger.info('Checking for existence on file-system...')
        # dems = dems[dems[FULLPATH].apply(lambda x: os.path.exists(x))==True]
    
    
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
    # Write list of IDs out
    if OUT_ID_LIST:
        logger.info('Writing list of DEM catalogids to file: {}'.format(OUT_ID_LIST))
        dem_ids = list(dems[CATALOGID1])
        if BOTH_IDS:
            dem_ids += list(dems[CATALOGID2])

        write_ids(dem_ids, OUT_ID_LIST)
    # Write list of filepaths to DEMs
    if OUT_FILEPATH_LIST:
        logger.info('Writing selected DEM system filepaths to: {}'.format(OUT_FILEPATH_LIST))
        filepaths = list(dems[FULLPATH])
        write_ids(filepaths, OUT_FILEPATH_LIST)

    #### Summary Statistics ####
    count = len(dems)
    min_date = dems[DATE_COL].min()
    max_date = dems[DATE_COL].max()
    if DENSITY_COL in list(dems):
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
    if DENSITY_COL in list(dems):
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
                        help='Coordinates to use rather than AOI shapefile. Lon Lat')
    parser.add_argument('--out_dem_footprint', type=os.path.abspath,
                        help="Path to write shapefile of selected DEMs.")
    parser.add_argument('--out_id_list', type=os.path.abspath,
                        help="Path to write text file of selected DEM's catalogids.")
    parser.add_argument('--both_ids', action='store_true',
                        help="Write both source IDs out.")
    parser.add_argument('--out_filepath_list', type=os.path.abspath,
                        help="Path to write text file of DEM's full paths.")
    parser.add_argument('--dems_footprint', type=os.path.abspath,
                        help='Path to DEM footprints')
    parser.add_argument('--months', nargs='+',
                        help='Months to include in selection, as intergers.')
    parser.add_argument('--min_date', type=str,
                        help='Minimum DEM date.')
    parser.add_argument('--max_date', type=str,
                        help='Maximum DEM date.')
    parser.add_argument('-r', '--resolution', type=float, choices=[0.5, 2.0, 2],
                        help='Restrict to a specific resolution.')
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
    BOTH_IDS = args.both_ids
    OUT_FILEPATH_LIST = args.out_filepath_list
    DEM_FP = args.dems_footprint
    MONTHS = args.months
    MIN_DATE = args.min_date
    MAX_DATE = args.max_date
    RES = args.resolution
    MULTISPEC = args.multispectral
    DENSITY_THRESH = args.density_threshold
    VALID_THRESH = args.valid_aoi_threshold

    dems = dem_selector(AOI_PATH=AOI_PATH,
                        COORDS=COORDS,
                        OUT_DEM_FP=OUT_DEM_FP,
                        OUT_ID_LIST=OUT_ID_LIST,
                        BOTH_IDS=BOTH_IDS,
                        OUT_FILEPATH_LIST=OUT_FILEPATH_LIST,
                        DEM_FP=DEM_FP,
                        MONTHS=MONTHS,
                        MIN_DATE=MIN_DATE,
                        MAX_DATE=MAX_DATE,
                        RES=RES,
                        MULTISPEC=MULTISPEC,
                        DENSITY_THRESH=DENSITY_THRESH,
                        VALID_THRESH=VALID_THRESH)
