# -*- coding: utf-8 -*-
"""
Select DEMs based on given parameters, including an AOI, date range, months, etc.
"""

import argparse
import logging.config
import os
import platform
import re
import sys

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

# from dem_utils.valid_data import valid_percent_clip
from valid_data import valid_percent
from selection_utils.db_utils import Postgres, generate_sql, intersect_aoi_where
# from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import write_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


# TODO: speed up by reprojecting once when warping/checking valid percentage (workaround impl.)
# TODO: change writing of dem FP with valid percents to actual location, not scratch
# TODO: Double check duplicate DEMS for each AOI


def get_bitmask_path(dem_path):
    bm_p = os.path.join(
        os.path.dirname(dem_path),
        os.path.basename(dem_path).replace('dem', 'bitmask')
    )

    return bm_p


def dem_selector(AOI_PATH=None, 
                 COORDS=None,
                 strips=True,
                 DEM_FP=None,
                 INTRACK=None,
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
    # TODO: Make this an arg: scenes or strips (if strips use Eriks gdb)
    DEM_SCENE_DB = 'sandwich-pool.dem'  # Sandwich DEM database
    DEM_SCENE_LYR =  'dem.scene_dem_master'  # Sandwich DEM footprint tablename
    DEM_STRIP_GDB = r'E:\disbr007\dem\setsm\footprints\dem_strips_v4_20200724.gdb'
    DEM_STRIP_LYR = 'dem_strips_v4_20200724'

    # These are only used when verifying that DEMs exist - not necessary for sandwich or Eriks gdb)
    WINDOWS_OS = 'Windows' # value returned by platform.system() for windows
    LINUX_OS = 'Linux' # value return by platform.system() for linux
    WINDOWS_LOC = 'win_path' # field name of windows path in footprint
    LINUX_LOC = 'filepath' # linux path field
    DEM_FNAME = 'dem_name' # field name with filenames (with ext)

    # PAIRNAME = 'pairname'

    fields = {
        'DEMS_GEOM': 'wkb_geometry',  # Sandwich DEMs geometry name
        # Used only for writing catalogids to text file if requested
        'CATALOGID1': 'catalogid1',  # field name in danco DEM footprint for catalogids
        'CATALOGID2': 'catalogid2',
        'DEM_ID': 'dem_id',
        'PAIRNAME': 'pairname',
        'FULLPATH': 'LOCATION',  # field name in footprint with path to dem file
        'BITMASK': 'bitmask',  # created field name in footprint to hold path to bitmask
        'DATE_COL': 'acqdate1',  # name of date field in dems footprint
        'DENSITY_COL': 'density',  # name of density field in dems footprint
        'SENSOR_COL': 'sensor1',  # name of sensor field in dems footprint
        'RES_COL': 'dem_res',
    }
    if strips:
        fields = {k: v.upper() for k, v in fields.items()}


    VALID_PERC = 'valid_perc'  # created field name in footprint to store valid %
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
    if AOI_PATH:
        logger.info('Reading AOI: {}'.format(AOI_PATH))
        aoi = gpd.read_file(AOI_PATH)
    elif COORDS:
        logger.info('Reading coordinates...')
        lon = float(COORDS[0])
        lat = float(COORDS[1])
        loc = Point(lon, lat)
        aoi = gpd.GeoDataFrame(geometry=[loc], crs="EPSG:4326")


    # Load DEM footprints from either local strips GDB or sandwich table
    if DEM_FP or strips:
        if not DEM_FP:
            logger.info('Loading DEMs footprint from: {}'.format(DEM_STRIP_GDB))
            dems = gpd.read_file(DEM_STRIP_GDB, layer=DEM_STRIP_LYR, driver='OpenFileGDB',
                                 bbox=aoi)
            logger.debug('DEMs footprint loaded: {:,}'.format(len(dems)))
        else:
            logger.info('Reading provided DEM footprint...')
            dems = gpd.read_file(DEM_FP)
            logger.debug('DEMs loaded: {;,}'.format(len(dems)))
        if MIN_DATE:
            dems = dems[dems[fields['DATE_COL']] > MIN_DATE]
            logger.debug('DEMs remaining after min_date > {}: {:,}'.format(MIN_DATE, len(dems)))
        if MAX_DATE:
            dems = dems[dems[fields['DATE_COL']] < MAX_DATE]
            logger.debug('DEMs remaining after max_date < {}: {:,}'.format(MAX_DATE, len(dems)))
        if RES:
            dems = dems[dems[fields['RES_COL']] == RES]
            logger.debug('DEMs remaining after resolution = {}: {:,}'.format(RES, len(dems)))
        if MULTISPEC:
            dems = dems[dems[fields['SENSOR_COL']].isin(['WV02', 'WV03'])]
            logger.debug('DEMs remaining after multispectral selction: {:,}'.format(len(dems)))
        if DENSITY_THRESH:
            dems = dems[dems[fields['DENSITY_COL']] > DENSITY_THRESH]
            logger.debug('DEMs remaining after density > {}: {:,}'.format(DENSITY_THRESH, len(dems)))
        if INTRACK:
            int_pat = re.compile('(WV01|WV02|WV03)')
            dems = dems[dems[fields['PAIRNAME']].str.contains(int_pat) == True]
            logger.debug('DEMs remaining after selecting only intrack: {:,}'.format(len(dems)))

        logger.debug('Remaining DEMs after initial subsetting: {:,}'.format(len(dems)))
        if aoi is not None:
            # Check coordinate system match and if not reproject AOI
            if aoi.crs != dems.crs:
                aoi = aoi.to_crs(dems.crs)

            logger.info('Selecting DEMs over AOI...')
            # Select by location
            dem_cols = list(dems)
            dems = gpd.sjoin(dems, aoi)
            dems = dems[dem_cols]

            # Remove duplicates resulting from intersection (not sure why DUPs)
            dems = dems.drop_duplicates(subset=(fields['DEM_ID']))

    else:
        # Load DEMs
        dems_where = ""
        if aoi is not None:
            # Get DEM footprint crs - this loads only one record, but it
            # will allow getting the crs of the footprints
            with Postgres(db_name=DEM_SCENE_DB) as dem_db:
                crs_sql = generate_sql(layer=DEM_SCENE_LYR, geom_col=fields['DEMS_GEOM'],
                                       encode_geom_col='geom', limit=1)
                # logger.debug(crs_sql)
                dems = dem_db.sql2gdf(sql=crs_sql)

            # Build SQL clause to select DEMs that intersect AOI
            # Reproject if necessary
            if aoi.crs != dems.crs:
                aoi = aoi.to_crs(dems.crs)
            # Create PostGIS intersection where clause
            dems_where = intersect_aoi_where(aoi=aoi, geom_col=fields['DEMS_GEOM'])

        # Add date constraints to SQL
        if MIN_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} > '{}'""".format(fields['DATE_COL'], MIN_DATE)
        if MAX_DATE:
            dems_where = check_where(dems_where)
            dems_where += """{} < '{}'""".format(fields['DATE_COL'], MAX_DATE)
        # Add resolution constraints
        if RES:
            dems_where = check_where(dems_where)
            dems_where += """{} = {}""".format(fields['RES_COL'], RES)
        # Add to SQL clause to just select multispectral sensors
        if MULTISPEC:
            dems_where = check_where(dems_where)
            dems_where += """{} IN ('WV02', 'WV03')""".format(fields['SENSOR_COL'])
        # Add density threshold to SQL
        if DENSITY_THRESH:
            dems_where = check_where(dems_where)
            dems_where += """{} > {}""".format(fields['DENSITY_COL'], DENSITY_THRESH)
        if INTRACK:
            dems_where = check_where(dems_where)
            intrack_wheres = ["""({} LIKE {})""".format(fields['PAIRNAME'], sensor)
                              for sensor in ['WV01', 'WV02', 'WV03']]
            dems_where += "({})".format(" OR ".join(intrack_wheres))

        # Load DEM footprints with SQL
        logger.info('Loading DEMs from {}.{}'.format(DEM_SCENE_DB, DEM_SCENE_LYR))
        with Postgres(db_name=DEM_SCENE_DB) as dem_db:
            dems_sql = generate_sql(layer=DEM_SCENE_LYR, where=dems_where)
            logger.debug('SQL: {}'.format(dems_sql))
            dems = dem_db.sql2gdf(sql=dems_sql, geom_col=fields['DEMS_GEOM'])
    
    # If only certain months requested, reduce to those
    if MONTHS:
        dems['temp_date'] = pd.to_datetime(dems[DATE_COL])
        dems[MONTH_COL] = dems['temp_date'].dt.month
        dems.drop(columns=['temp_date'], inplace=True)
        dems = dems[dems[MONTH_COL].isin(MONTHS)]


    logger.info('DEMs found matching specifications: {:,}'.format(len(dems)))
    if len(dems) == 0:
        logger.error('No DEMs found matching specifications, exiting...')
        sys.exit()
    
    # Create full path to server location, used for checking validity
    # Determine operating system for locating DEMs
    if LOCATE_DEMS:
        OS = platform.system()
        if OS == WINDOWS_OS:
            server_loc = WINDOWS_LOC
        elif OS == LINUX_OS:
            server_loc = LINUX_LOC
        dems[fields['FULLPATH']] = dems.apply(lambda x: os.path.join(x[server_loc], x[DEM_FNAME]), axis=1)
        # This was removed after DEMs moved to tape
        # # Subset to only those DEMs that actually can be found
        # logger.info('Checking for existence on file-system...')
        # dems = dems[dems[FULLPATH].apply(lambda x: os.path.exists(x))==True]
    
    
    #### GET VALID DATA PERCENT ####
    if VALID_THRESH:
        logger.info('Determining percent of non-NoData pixels over AOI for each DEM...')
        dems[fields['BITMASK']] = dems[fields['FULLPATH']].apply(lambda x: get_bitmask_path(x))

        dems[VALID_PERC] = -9999.0
        for row in tqdm(dems[[fields['FULLPATH'], VALID_PERC]].itertuples(index=True),
                        total=len(dems)):
            vp = valid_data_percent(gdal_ds=row[1])
            # vp = valid_percent_clip(AOI_PATH, row[1]) # Index is row[0], then passed columns
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
        dem_ids = list(dems[fields['CATALOGID1']])
        if BOTH_IDS:
            dem_ids += list(dems[fields['CATALOGID2']])
        write_ids(dem_ids, OUT_ID_LIST)
    # Write list of filepaths to DEMs
    if OUT_FILEPATH_LIST:
        logger.info('Writing selected DEM system filepaths to: {}'.format(OUT_FILEPATH_LIST))
        filepaths = list(dems[fields['FULLPATH']])
        write_ids(filepaths, OUT_FILEPATH_LIST)

    #### Summary Statistics ####
    count = len(dems)
    min_date = dems[fields['DATE_COL']].min()
    max_date = dems[fields['DATE_COL']].max()
    if fields['DENSITY_COL'] in list(dems):
        min_density = dems[fields['DENSITY_COL']].min()
        max_density = dems[fields['DENSITY_COL']].max()
        avg_density = dems[fields['DENSITY_COL']].mean()
    if VALID_THRESH:
        min_valid = dems[VALID_PERC].min()
        max_valid = dems[VALID_PERC].max()
        avg_valid = dems[VALID_PERC].mean()

    logger.info("SUMMARY of DEM SELECTION:")
    logger.info("Number of DEMs: {:,}".format(count))
    logger.info("Earliest date: {}".format(min_date))
    logger.info("Latest date: {}".format(max_date))
    if fields['DENSITY_COL'] in list(dems):
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
    # parser.add_argument('--dem_source', type=str, choices=['scene_dem', ])
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
    parser.add_argument('--intrack', action='store_true',
                        help='Select only intrack stereo.')
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
    parser.add_argument('--scenes', action='store_true',
                        help="Use to select scenes from sandwich-pool.scene_dem rather than strips.")

    args = parser.parse_args()

    AOI_PATH = args.aoi_path
    COORDS = args.coords
    OUT_DEM_FP = args.out_dem_footprint
    OUT_ID_LIST = args.out_id_list
    BOTH_IDS = args.both_ids
    OUT_FILEPATH_LIST = args.out_filepath_list
    DEM_FP = args.dems_footprint
    INTRACK = args.intrack
    MONTHS = args.months
    MIN_DATE = args.min_date
    MAX_DATE = args.max_date
    RES = args.resolution
    MULTISPEC = args.multispectral
    DENSITY_THRESH = args.density_threshold
    VALID_THRESH = args.valid_aoi_threshold
    strips = not args.scenes

    dems = dem_selector(AOI_PATH=AOI_PATH,
                        COORDS=COORDS,
                        OUT_DEM_FP=OUT_DEM_FP,
                        OUT_ID_LIST=OUT_ID_LIST,
                        BOTH_IDS=BOTH_IDS,
                        OUT_FILEPATH_LIST=OUT_FILEPATH_LIST,
                        DEM_FP=DEM_FP,
                        INTRACK=INTRACK,
                        MONTHS=MONTHS,
                        MIN_DATE=MIN_DATE,
                        MAX_DATE=MAX_DATE,
                        RES=RES,
                        MULTISPEC=MULTISPEC,
                        DENSITY_THRESH=DENSITY_THRESH,
                        VALID_THRESH=VALID_THRESH,
                        strips=strips)
