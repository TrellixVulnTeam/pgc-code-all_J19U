# -*- coding: utf-8 -*-
"""
Select DEMs based on given parameters, including an AOI, date range, months, etc.
"""

import argparse
import logging.config
import os
import platform
from pathlib import Path
import re
import sys

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

from .dem_utils import get_aux_file, nunatak2windows, get_dem_image1_id
from .valid_data import valid_percent
from selection_utils.db import Postgres, generate_sql, intersect_aoi_where
# from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import read_ids, write_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

# TODO: speed up by reprojecting once when warping/checking valid percentage (workaround impl.)
# TODO: change writing of dem FP with valid percents to actual location, not scratch
# TODO: Double check duplicate DEMS for each AOI

IS_XTRACK = 'IS_XTRACK'


def dem_selector(AOI_PATH=None, 
                 COORDS=None,
                 SELECT_IDS_PATH=None,
                 select_field=None,
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
                 CALC_VALID=False,
                 VALID_ON='dem',
                 VALID_THRESH=None,
                 OUT_DEM_FP=None,
                 OUT_ID_LIST=None,
                 BOTH_IDS=False,
                 IMAGE1_IDS=False,
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
    SELECT_IDS_PATH : os.path.abspath
        Path to text file of DEM IDs to select.
    select_field : list
        Name of field(s) in DEM database to select IDs in SELECT_IDS_PATH from
    strips : bool
        True to select from strip DEM database, False to use scenes database
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
    DEM_SCENE_LYR = 'dem.scene_dem_master'  # Sandwich DEM footprint tablename
    # TODO: Move this to a config file with MFP location
    DEM_STRIP_GDB = r'E:\disbr007\dem\setsm\footprints\dem_strips_v4_20201120.gdb'
    DEM_STRIP_LYR = Path(DEM_STRIP_GDB).stem #'dem_strips_v4_20201120'
    DEM_STRIP_GDB_CRS = 'epsg:4326'

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
        'SCENEDEMID': 'scenedemid',
        'STRIPDEMID': 'stripdemid',
        'CATALOGID1': 'catalogid1',  # field name in danco DEM footprint for catalogids
        'CATALOGID2': 'catalogid2',
        'DEM_ID': 'dem_id',
        'PAIRNAME': 'pairname',
        'LOCATION': 'LOCATION',  # field name in footprint with path to dem file
        'PLATFORM_PATH': 'PLATFORM_PATH', # ceated field with platform specfic path to dem file
        'VALID_ON': 'VALID_ON', # created field name to hold path to file to calc valid on (bitmask, 10m, etc)
        'BITMASK': 'bitmask',  # created field name in footprint to hold path to bitmask
        'DATE_COL': 'acqdate1',  # name of date field in dems footprint
        'DENSITY_COL': 'density',  # name of density field in dems footprint
        'SENSOR_COL': 'sensor1',  # name of sensor field in dems footprint
        'RES_COL': 'dem_res',
    }
    if strips:
        fields = {k: v.upper() for k, v in fields.items()}

    # Created fields
    VALID_PERC = 'valid_perc'  # created field name in footprint to store valid percent
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
    else:
        aoi = None


    # Load DEM footprints from either local strips GDB or sandwich table
    if DEM_FP or strips:
        # Load DEM index or footprint
        if not DEM_FP:
            logger.info('Loading DEMs footprint from: {}'.format(DEM_STRIP_GDB))
            if aoi.crs != DEM_STRIP_GDB_CRS:
                aoi_bbox = aoi.to_crs(DEM_STRIP_GDB_CRS)
            else:
                aoi_bbox = aoi
            dems = gpd.read_file(DEM_STRIP_GDB, layer=DEM_STRIP_LYR,
                                 driver='OpenFileGDB',
                                 bbox=aoi_bbox)
            logger.debug('DEMs footprint loaded: {:,}'.format(len(dems)))
        else:
            logger.info('Reading provided DEM footprint...')
            dems = gpd.read_file(DEM_FP)
            logger.debug('DEMs loaded: {;,}'.format(len(dems)))

        # Subset by parameters provided
        if SELECT_IDS_PATH:
            select_ids = read_ids(SELECT_IDS_PATH)
            try:
                dems = dems[dems[select_field].isin(select_ids)]
            except KeyError:
                logger.error("Field '{}' not found in DEM footprint. "
                             "Available fields:\n"
                             "{}".format(select_field, '\n'.join(list(dems))))
            logger.debug('DEMs remaining after:'
                         ' {} in {}'.format(select_field, select_ids))
        if MIN_DATE:
            dems = dems[dems[fields['DATE_COL']] > MIN_DATE]
            logger.debug('DEMs remaining after min_date > {}: '
                         '{:,}'.format(MIN_DATE, len(dems)))
        if MAX_DATE:
            dems = dems[dems[fields['DATE_COL']] < MAX_DATE]
            logger.debug('DEMs remaining after max_date < {}: '
                         '{:,}'.format(MAX_DATE, len(dems)))
        if RES:
            dems = dems[dems[fields['RES_COL']] == RES]
            logger.debug('DEMs remaining after resolution = {}: '
                         '{:,}'.format(RES, len(dems)))
        if MULTISPEC:
            dems = dems[dems[fields['SENSOR_COL']].isin(['WV02', 'WV03'])]
            logger.debug('DEMs remaining after multispectral selection: '
                         '{:,}'.format(len(dems)))
        if DENSITY_THRESH:
            dems = dems[dems[fields['DENSITY_COL']] > DENSITY_THRESH]
            logger.debug('DEMs remaining after density > {}: '
                         '{:,}'.format(DENSITY_THRESH, len(dems)))
        if INTRACK:
            dems = dems[dems[IS_XTRACK] == 0]
            # int_pat = re.compile('(WV01|WV02|WV03)')
            # dems = dems[dems[fields['PAIRNAME']].str.contains(int_pat) == True]
            logger.debug('DEMs remaining after selecting only intrack: '
                         '{:,}'.format(len(dems)))

        logger.debug('Remaining DEMs after initial subsetting: '
                     '{:,}'.format(len(dems)))
        if len(dems) == 0:
            logger.warning('No DEMS found.')
            # sys.exit()

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
        if SELECT_IDS_PATH:
            select_ids = read_ids(SELECT_IDS_PATH)
            ids_where = ["""{} IN ({})""".format(sf, str(select_ids)[1:-1]) for sf in select_field]
            ids_where = "({})".format(" OR ".join(ids_where))
            dems_where = check_where(dems_where)
            dems_where += ids_where
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
        dems['temp_date'] = pd.to_datetime(dems[fields['DATE_COL']])
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

            dems[fields['PLATFORM_PATH']] = dems[fields['LOCATION']].apply(lambda x: nunatak2windows(x))
        elif OS == LINUX_OS:
            dems[fields['PLATFORM_PATH']] = dems[fields['LOCATION']]

        # This was removed after DEMs moved to tape
        # # Subset to only those DEMs that actually can be found
        # logger.info('Checking for existence on file-system...')
        # dems = dems[dems[fields['PLATFORM_PATH']].apply(lambda x: os.path.exists(x))==True]
    
    
    #### GET VALID DATA PERCENT ####
    if CALC_VALID:
        # TODO: convert to valid aoi w/in bounds of footprint
        logger.info('Determining percent of non-NoData pixels over AOI for each DEM using *_{}...'.format(VALID_ON))
        dems[fields['VALID_ON']] = dems[fields['PLATFORM_PATH']].\
            apply(lambda x: get_aux_file(dem_path=x, aux_file=VALID_ON))

        dems[VALID_PERC] = -9999.0
        for row in tqdm(dems[[fields['VALID_ON'], VALID_PERC]].itertuples(index=True),
                        total=len(dems)):
            vp = valid_percent(gdal_ds=row[1])
            dems.at[row.Index, VALID_PERC] = vp
        if VALID_THRESH:
            dems = dems[dems[VALID_PERC] > VALID_THRESH]

    #### WRITE FOOTPRINT AND TXT OF MATCHES ####
    # Write footprint out
    if OUT_DEM_FP:
        logger.info('Writing DEMs footprint to file: {}'.format(OUT_DEM_FP))
        dems.to_file(OUT_DEM_FP)
    # Write list of IDs out
    if OUT_ID_LIST:
        logger.info('Writing list of DEM catalogids to file: '
                    '{}'.format(OUT_ID_LIST))
        if IMAGE1_IDS:
            logger.info('Locating Image 1 IDs for each DEM...')
            dems['META_TXT'] = dems[fields['PLATFORM_PATH']]. \
                apply(lambda x: get_aux_file(dem_path=x, aux_file='meta'))
            dems['Image1_cid'] = dems['META_TXT'].apply(lambda x: get_dem_image1_id(x))
            dem_ids = list(set(dems['Image1_cid']))
        else:
            dem_ids = list(dems[fields['CATALOGID1']])
            if BOTH_IDS:
                dem_ids += list(dems[fields['CATALOGID2']])
        write_ids(dem_ids, OUT_ID_LIST)
    # Write list of filepaths to DEMs
    if OUT_FILEPATH_LIST:
        logger.info('Writing selected DEM system filepaths to: '
                    '{}'.format(OUT_FILEPATH_LIST))
        try:
            filepaths = list(dems[fields['PLATFORM_PATH']])
        except KeyError as e:
            logger.error('PLATOFRM_PATH field not found - use --locate_dems '
                         'flag to generate field.')
            logger.error(e)
            sys.exit()
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
    aux_files = ['dem', 'bitmask', '10m_shade',
                 '10m_shade_masked', 'matchtag', 'ortho']

    parser = argparse.ArgumentParser()

    id_write_group = parser.add_mutually_exclusive_group()

    parser.add_argument('--aoi_path', type=os.path.abspath,
                        help='Path to AOI to select DEMs over.')
    parser.add_argument('--coords', nargs='+',
                        help='Coordinates to use rather than AOI shapefile. '
                             'Lon Lat')
    parser.add_argument('--select_ids', type=os.path.abspath,
                        help='List of IDs to select. Specify field in DEM index'
                             ' to select from using "--select_field"')
    parser.add_argument('--select_field', type=str, action='append',
                        help='Field in DEM index to select IDs in --select_ids '
                             'from.')
    # parser.add_argument('--dem_source', type=str, choices=['scene_dem', ])
    parser.add_argument('--out_dem_footprint', type=os.path.abspath,
                        help="Path to write shapefile of selected DEMs.")
    parser.add_argument('--out_id_list', type=os.path.abspath,
                        help="Path to write text file of selected DEM's "
                             "catalogids.")
    id_write_group.add_argument('--both_ids', action='store_true',
                        help="Write both source IDs out.")
    id_write_group.add_argument('--image1_ids', action='store_true',
                        help='Write Image1 Ids out using *_meta.txt file.')
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
                        help='Use to select only DEMs from multispectral '
                             'sources.')
    parser.add_argument('--density_threshold', type=float,
                        help='Minimum density to include in selection.')
    parser.add_argument('--valid_threshold', type=float,
                        help="""Threshold percent of non-Nodata pixels for each
                         DEM. Not recommended for large selections.""")
    parser.add_argument('--calc_valid', action='store_true',
                        help='Use to calculate percent non-NoData pixels for '
                             'each DEM.')
    parser.add_argument('--valid_on', type=str, choices=aux_files,
                        help='DEM or auxillary file to calculate percent valid '
                             'on.')
    parser.add_argument('--scenes', action='store_true',
                        help="Use to select scenes from sandwich-pool.scene_dem"
                             " rather than strips.")
    parser.add_argument('--locate_dems', action='store_true',
                        help='Use to verify existence of DEMs. Required if '
                             'using --calc_valid')

    # os.chdir(r'E:\disbr007\umn\accuracy_assessment\mj_ward1')
    # sys.argv = [r'C:\code\pgc-code-all\dem_utils\dem_selector.py',
    #             '--aoi_path', r'aoi\mj_ward1_3413.shp',
    #             '--out_dem_footprint', r'scratch\all_dems_2m_06_07_08_09_ms',
    #             '--calc_valid', '--valid_on', 'matchtag']

    args = parser.parse_args()

    AOI_PATH = args.aoi_path
    COORDS = args.coords
    select_ids_path = args.select_ids
    select_field = args.select_field
    OUT_DEM_FP = args.out_dem_footprint
    OUT_ID_LIST = args.out_id_list
    BOTH_IDS = args.both_ids
    IMAGE1_IDS = args.image1_ids
    OUT_FILEPATH_LIST = args.out_filepath_list
    DEM_FP = args.dems_footprint
    INTRACK = args.intrack
    MONTHS = args.months
    MIN_DATE = args.min_date
    MAX_DATE = args.max_date
    RES = args.resolution
    MULTISPEC = args.multispectral
    DENSITY_THRESH = args.density_threshold
    CALC_VALID = args.calc_valid
    VALID_ON = args.valid_on
    VALID_THRESH = args.valid_threshold
    LOCATE_DEMS = args.locate_dems
    strips = not args.scenes

    dems = dem_selector(AOI_PATH=AOI_PATH,
                        COORDS=COORDS,
                        SELECT_IDS_PATH=select_ids_path,
                        select_field=select_field,
                        OUT_DEM_FP=OUT_DEM_FP,
                        OUT_ID_LIST=OUT_ID_LIST,
                        BOTH_IDS=BOTH_IDS,
                        IMAGE1_IDS=IMAGE1_IDS,
                        OUT_FILEPATH_LIST=OUT_FILEPATH_LIST,
                        DEM_FP=DEM_FP,
                        INTRACK=INTRACK,
                        MONTHS=MONTHS,
                        MIN_DATE=MIN_DATE,
                        MAX_DATE=MAX_DATE,
                        RES=RES,
                        MULTISPEC=MULTISPEC,
                        DENSITY_THRESH=DENSITY_THRESH,
                        CALC_VALID=CALC_VALID,
                        VALID_ON=VALID_ON,
                        VALID_THRESH=VALID_THRESH,
                        LOCATE_DEMS=LOCATE_DEMS,
                        strips=strips)
