# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import argparse
import datetime
import logging.config
import os
import sys

import arcpy

# from misc_utils.id_parse_utils import read_ids, pgc_index_path
from misc_utils.logging_utils import create_logger


def pgc_index_path(ids=False):
    """
    Return the path to the most recent pgc index from a manually updated
    text file containing the path.
    """
    with open(r'C:\code\pgc-code-all\config\pgc_index_path.txt', 'r') as src:
        content = src.readlines()
    if not ids:
        index_path = content[0].strip('\n')
    if ids:
        index_path = content[1].strip   ('\n')
    logger.debug('PGC index path loaded: {}'.format(index_path))

    return index_path


def read_ids(ids_file, field=None):
    """
    Read ids from a variety of file types.
    Field only required if providing shapefile.
    """
    # Determine file type
    ext = os.path.splitext(ids_file)[1]
    if ext in ['.txt', '.csv']:
        with open(ids_file, 'r') as f:
            content = f.readlines()
            # Remove any whitespace
            ids = [l.strip() for l in content]
    elif ext == '.shp':
        with arcpy.da.SearchCursor(ids_file, [field]) as cursor:
            ids = [row[0] for row in cursor]
    else:
        logger.warning('Extension {} not supported.'.format(ext))
    # Remove any duplicate IDs
    ids = set(ids)

    return ids


def check_where(where):
    """Formatting helper function for SQL clause"""
    if where:
        where += ' AND '
    return where


def determine_input_type(selector_path, selector_field):
    """
    Determine the type of selector provided (.shp or .txt)
    based on the extension.
    """
    ext = os.path.basename(selector_path).split('.')[1]

    if ext in ['shp', 'geojson'] and not selector_field:
        input_type = 'location'
    else:
        input_type = 'ids'

    return input_type


def danco_connection(db, layer):
    """Create a connection to danco"""
    arcpy.env.overwriteOutput = True

    # Local variables:
    arcpy_cxn = "C:\\dbconn\\arcpy_cxn"
    # arcpy_footprint_MB_sde = arcpy_cxn

    # Process: Create Database Connection
    cxn = arcpy.CreateDatabaseConnection_management(arcpy_cxn,
                                                    "{}_arcpy.sde".format(db),
                                                    "POSTGRESQL",
                                                    "danco.pgc.umn.edu",
                                                    "DATABASE_AUTH",
                                                    "disbr007",
                                                    "ArsenalFC10",
                                                    "SAVE_USERNAME",
                                                    "{}".format(db),
                                                    "",
                                                    "TRANSACTIONAL",
                                                    "sde.DEFAULT",
                                                    "")

    arcpy.env.workspace = os.path.join("C:\\dbconn\\arcpy_cxn", "{}_arcpy.sde".format(db))

    return '{}.sde.{}'.format(db, layer)


def place_name_AOI(place_name, selector_path):
    """Create a layer of a placename from danco acan DB."""
    where = """gaz_name = '{}'""".format(place_name)
    place_name_layer_p = danco_connection('acan', 'ant_gnis_pt')
    aoi = arcpy.MakeFeatureLayer_management(place_name_layer_p, out_layer='place_name_lyr',
                                            where_clause=where)
    arcpy.CopyFeatures_management(aoi, selector_path)

    return selector_path


def create_points(coords, shp_path):
    """Create a point shapefile from long, lat pairs."""
    # TODO: Use arcpy to create points, remove gpd as dependency
    # import geopandas as gpd
    # from shapely.geometry import Point

    # logger.info('Creating point shapefile from long, lat pairs(s)...')
    # points = [Point(float(pair.split(',')[0]), float(pair.split(',')[1])) for pair in coords]
    # gdf = gpd.GeoDataFrame(geometry=points, crs={'init': 'epsg:4326'})
    # gdf.to_file(shp_path)
    clean_coords = [[float(x.strip("'")), float(y.strip("'"))] for c in coords for x, y in [c.split(',')]]
    out_path = os.path.dirname(shp_path)
    out_name = os.path.basename(shp_path)
    logger.debug('Creating point layer from coordinates at:\nout_path:{} \nout_name:{}'.format(out_path, out_name))
    spatial_ref = arcpy.SpatialReference(4326)
    arcpy.CreateFeatureclass_management(out_path=out_path,
                                        out_name=out_name,
                                        geometry_type="POINT",
                                        spatial_reference=spatial_ref)

    with arcpy.da.InsertCursor(shp_path, ['SHAPE@']) as cursor:
        for c in clean_coords:
            cursor.insertRow([arcpy.Point(c[0], c[1])])
    logger.debug('Point feature class created from coordinates at: {}'.format(shp_path))


def select_footprints(selector_path, input_type, imagery_index, overlap_type, search_distance, id_field,
                      selector_field):
    """Select footprints from MFP given criteria"""
    if input_type == 'shp' and not selector_field:
        # if not id_field:
        # Select by location
        logger.info('Performing selection by location...')
        logger.info('Loading index: {}'.format(imagery_index))
        idx_lyr = arcpy.MakeFeatureLayer_management(imagery_index)
        logger.info('Loading AOI: {}'.format(selector_path))
        aoi_lyr = arcpy.MakeFeatureLayer_management(selector_path)
        logger.info('Making selection...')
        selection = arcpy.SelectLayerByLocation_management(idx_lyr,
                                                           overlap_type,
                                                           aoi_lyr,
                                                           selection_type="NEW_SELECTION",
                                                           search_distance=search_distance)

    else:
        # Initial selection by id
        logger.info('Reading in IDs from: {}...'.format(os.path.basename(selector_path)))
        ids = sorted(read_ids(selector_path, field=selector_field))
        unique_ids = set(ids)
        logger.info('Total source IDs found: {}'.format(len(ids)))
        logger.info('Unique source IDs found: {}'.format(len(unique_ids)))
        logger.debug('IDs:\n{}'.format('\n'.join(ids)))
        ids_str = str(ids)[1:-1]
        where = """{} IN ({})""".format(id_field, ids_str)
        logger.debug('Where clause for ID selection: {}\n'.format(where))

        logger.info('Making selection...')
        selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)

        # count = int(result.getOutput(0))
        result = arcpy.GetCount_management(selection)
        count = int(result.getOutput(0))
        logger.debug('Selected features: {}'.format(count))
        if count == 0:
            logger.warning('No features found, exiting...')
            sys.exit()

        if id_field:
            with arcpy.da.SearchCursor(selection, [id_field]) as cursor:
                selected_ids = [row[0] for row in cursor]
                num_selection_ids = len(set(selected_ids))
            # TODO: This is not reporting the correct number of unique IDs
            logger.debug('Selected IDs:\n{}'.format('\n'.join([str((i, each_id)) for i, each_id in enumerate(selected_ids)])))
            logger.info('Unique {} found in selection: {}'.format(id_field, num_selection_ids))

    return selection


def select_by_id(ids, imagery_index, id_field='CATALOG_ID'):
    """Select scene footprints from the master footprint by ID"""
    logger.info('Selecting by IDs...')
    ids_str = str(ids)[1:-1]
    where = """{} IN ({})""".format(id_field, ids_str)
    logger.debug('Where clause for ID selection: {}\n'.format(where))

    logger.info('Making selection...')
    selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)

    return selection


def select_by_location(aoi_path, imagery_index, overlap_type, search_distance):
    """Select scene footprints from master footprint by location with AOI"""
    logger.info('Performing selection by location...')
    logger.info('Loading index: {}'.format(imagery_index))
    idx_lyr = arcpy.MakeFeatureLayer_management(imagery_index)
    logger.info('Loading AOI: {}'.format(selector_path))
    aoi_lyr = arcpy.MakeFeatureLayer_management(aoi_path)
    logger.info('Making selection...')
    selection = arcpy.SelectLayerByLocation_management(idx_lyr,
                                                       overlap_type,
                                                       aoi_lyr,
                                                       selection_type="NEW_SELECTION",
                                                       search_distance=search_distance)

    return selection


def select_dates(src, min_year, max_year, months):
    """Select by years and months"""
    year_sql = """ "acq_time" > '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
    month_terms = [""" "acq_time" LIKE '%-{}-%'""".format(month) for month in months]
    month_sql = " OR ".join(month_terms)
    sql = """({}) AND ({})""".format(year_sql, month_sql)

    # Faster by far than SelectByAttributes
    selection = arcpy.MakeFeatureLayer_management(src, where_clause=sql)
    return selection


def write_shp(selection, out_path):
    logger.info('Creating shapefile of selection...')
    out_shp = arcpy.CopyFeatures_management(selection, out_path)
    logger.info('Shapefile of selected features created at: {}'.format(out_path))
    count = arcpy.GetCount_management(selection)[0]
    logger.info('Features in shapefile: {}'.format(count))
    return out_shp


if __name__ == '__main__':
    # Default arguments
    argdef_sensors          = ['QB02', 'IK01', 'GE01', 'WV01', 'WV02', 'WV03']
    argdef_prod_code        = ['M1BS', 'P1BS']
    argdef_min_year         = '1900'
    argdef_max_year         = '9999'
    argdef_months           = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    argdef_overlap_type     = 'INTERSECT'
    argdef_overlap_type_choices = ["INTERSECT", "INTERSECT_3D", "WITHIN_A_DISTANCE", "WITHIN_A_DISTANCE_3D",
                                   "WITHIN_A_DISTANCE_GEODESIC", "CONTAINS", "COMPLETELY_CONTAINS", "CONTAINS_CLEMENTINI",
                                   "WITHIN", "COMPLETELY_WITHIN", "WITHIN_CLEMENTINI", "ARE_IDENTICAL_TO", "BOUNDARY_TOUCHES",
                                   "SHARE_A_LINE_SEGMENT_WITH", "CROSSED_BY_THE_OUTLINE_OF", "HAVE_THEIR_CENTER_IN"]
    argdef_search_distance  = 0
    argdef_place_name       = None
    argdef_coordinate_pairs = None
    # argdef_id_field         = 'CATALOG_ID'
    argdef_id_field         = None

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('out_path', type=os.path.abspath, help='Path to write selection shp file.')
    parser.add_argument('-s', '--selector_path', type=os.path.abspath,
                        help='''The path to the selector to use. This can be an AOI .shp file or
                        .txt file of ids. If .txt, --id_field is required. If providing coordinates
                        or placename, the path to write the created AOI shapefile to.''')
    parser.add_argument('--id_field', type=str, default=argdef_id_field,
                        help='''If using a .txt file of ids for the selection, specify here the
                        type of ids in the .txt, i.e. the field in the master footprint to select by.:
                        e.g.: CATALOG_ID, SCENE_ID, etc.''')
    parser.add_argument('--selector_field', type=str,
                        help='If selector is shp, and select by ID desired, the field name to pull IDs from.')
    parser.add_argument('--secondary_selector', type=os.path.abspath,
                        help='Path to an AOI layer to combine with an initial ID selection.')
    parser.add_argument('--prod_code', type=str, nargs='+', default=argdef_prod_code,
                        help='Prod code to select. E.g. P1BS, M1BS')
    parser.add_argument('--sensors', nargs='+', default=argdef_sensors,
                        help='Sensors to include.')
    parser.add_argument('--spec_type', nargs='+',
                        help='spec_type to include. eg. SWIR Multispectral')
    parser.add_argument('--min_year', type=str, default=argdef_min_year,
                        help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, default=argdef_max_year,
                        help='Latest year to include')
    parser.add_argument('--months', nargs='+',
                        default=argdef_months,
                        help='Months to include. E.g. 01 02 03')
    parser.add_argument('--max_cc', type=float, help='Max cloudcover to include.')
    parser.add_argument('--max_off_nadir', type=int, help='Max off_nadir angle to include')
    parser.add_argument('--overlap_type', type=str, default=argdef_overlap_type, choices=argdef_overlap_type_choices,
                        help='''Type of select by location to perform. Must be one of:
                            the options available in ArcMap. E.g.: 'INTERSECT', 'WITHIN',
                            'CROSSED_BY_OUTLINE_OF', etc.''')
    parser.add_argument('--search_distance', type=str, default=argdef_search_distance,
                        help='''Search distance for overlap_types that support.
                        E.g. "10 Kilometers"''')
    parser.add_argument('--coordinate_pairs', nargs='*', default=argdef_coordinate_pairs,
                        help='Longitude, latitude pairs. x1,y1 x2,y2 x3,y3, etc.')
    parser.add_argument('--place_name', type=str, default=argdef_place_name,
                        help='Select by Antarctic placename from acan danco DB.')
    parser.add_argument('--override_defaults', action='store_true',
                        help="""Use this flag to not use any default attribute selection
                                parameters: prod_code, sensors, spec_type, max_cc,
                                max_off_nadir""")
    parser.add_argument('--dryrun', action='store_true',
                        help='Print information about selection, but do not write.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set logging level to DEBUG.')

    args = parser.parse_args()

    if args.verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'

    logger = create_logger(__name__, 'sh', handler_level)
    # logging.config.dictConfig(LOGGING_CONFIG(handler_level))
    # logger = logging.getLogger(__name__)

    # Parse args variables
    out_path = args.out_path
    selector_path = args.selector_path
    id_field = args.id_field
    selector_field = args.selector_field
    secondary_selector = args.secondary_selector
    prod_code = args.prod_code
    sensors = args.sensors
    spec_type = args.spec_type
    min_year = args.min_year
    max_year = args.max_year
    months = args.months
    max_cc = args.max_cc
    max_off_nadir = args.max_off_nadir
    overlap_type = args.overlap_type
    search_distance = args.search_distance
    coordinate_pairs = args.coordinate_pairs
    place_name = args.place_name
    override_defaults = args.override_defaults
    dryrun = args.dryrun

    imagery_index = pgc_index_path()
    arcpy.env.overwriteOutput = True

    # If coordinate pairs create shapefile
    if coordinate_pairs:
        logger.info('Using coordinate pairs:\n{}'.format(coordinate_pairs))
        create_points(coordinate_pairs, selector_path)

    # If place name provided, use as AOI layer
    if place_name is not None:
        place_name_AOI(place_name, selector_path)

    # Inital selection by location or ID
    # logger.info('Making selection...')
    # selection = select_footprints(selector_path=selector_path,
    #                               input_type=determine_input_type(selector_path),
    #                               imagery_index=imagery_index,
    #                               overlap_type=overlap_type,
    #                               search_distance=search_distance,
    #                               id_field=id_field,
    #                               selector_field=selector_field)

    input_type = determine_input_type(selector_path, selector_field)

    if input_type == 'location':
        selection = select_by_location(aoi_path=selector_path,
                                       imagery_index=imagery_index,
                                       overlap_type=overlap_type,
                                       search_distance=search_distance)
        
    elif input_type == 'ids':
        ids = read_ids(selector_path, field=selector_field)
        unique_ids = set(ids)
        logger.info('Source IDs found: {}'.format(len(ids)))
        logger.info('Unique source IDs: {}'.format(len(unique_ids)))
        logger.debug('\n{}'.format('\n'.join(unique_ids)))

        selection = select_by_id(ids=unique_ids,
                                 imagery_index=imagery_index,
                                 id_field=id_field)

        with arcpy.da.SearchCursor(selection, [id_field]) as cursor:
            unique_selected_ids = set([row[0] for row in cursor])
        logger.info('Unique selected IDs: {}'.format(len(unique_selected_ids)))
        # logger.info('Unique Selected IDs:\n{}'.format('\n'.join(unique_selected_ids)))

        if len(unique_ids) != len(unique_selected_ids):
            logger.warning('Not all IDs found in MFP, missing IDs:\n{}'.format('\n'.join(list(unique_ids-unique_selected_ids))))
        
    if secondary_selector:
        logger.info('Selecting within secondary selector...')
        aoi_lyr = arcpy.MakeFeatureLayer_management(secondary_selector)
        selection = arcpy.SelectLayerByLocation_management(selection,
                                                           overlap_type,
                                                           aoi_lyr,
                                                           selection_type="SUBSET_SELECTION",
                                                           search_distance=search_distance)
        result = arcpy.GetCount_management(selection)
        count = int(result.getOutput(0))
        logger.debug('Selected features: {}'.format(count))

    # Initialize an empty where clause
    where = ''
    if not override_defaults:
        # CC20 if specified
        if max_cc:
            if max_cc > 1:
                logger.warning('Cloudcovers in MFP are specified as porportions from 0.0 - 1.0. Converting {} to this scale.'.format(max_cc))
                max_cc = max_cc / 100
                logger.debug('max_cc: {}'.format(max_cc))
            where = check_where(where)
            where += """(cloudcover <= {})""".format(max_cc)
        # PROD_CODE if sepcified
        if prod_code:
            if prod_code != ['any']:
                where = check_where(where)
                prod_code_str = str(prod_code)[1:-1]
                where += """(prod_code IN ({}))""".format(prod_code_str)
        # Selection by sensor if specified
        if sensors:
            where = check_where(where)
            sensors_str = str(sensors)[1:-1]
            where += """(sensor IN ({}))""".format(sensors_str)
        # Time selection
        if min_year != argdef_min_year or max_year != argdef_max_year or months != argdef_months:
            where = check_where(where)
            year_sql = """ "acq_time" > '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
            month_terms = [""" "acq_time" LIKE '%-{}-%'""".format(month) for month in months]
            month_sql = " OR ".join(month_terms)
            where += """({}) AND ({})""".format(year_sql, month_sql)
        if max_off_nadir:
            where = check_where(where)
            off_nadir_sql = """(off_nadir < {})""".format(max_off_nadir)
            where += off_nadir_sql
        if spec_type:
            where = check_where(where)
            spec_type_str = str(spec_type)[1:-1]
            spec_type_sql = """(spec_type IN ({}))""".format(spec_type_str)
            where += spec_type_sql
    logger.debug('Where clause for non-ID attribute selection: {}'.format(where))
    # Subset selection by attributes.
    selection = arcpy.MakeFeatureLayer_management(selection, where_clause=where)

    # Selection by date if specified
    selection = select_dates(selection, min_year=min_year, max_year=max_year, months=months)

    # Print number of selected features
    result = arcpy.GetCount_management(selection)
    count = int(result.getOutput(0))
    logger.info('Selected features: {}'.format(count))
    if id_field:
        with arcpy.da.SearchCursor(selection, [id_field]) as cursor:
            selected_ids = [row[0] for row in cursor]
            num_selection_ids = len(set(selected_ids))
        # TODO: This is not reporting the correct number of unique IDs
        logger.debug(
            'Selected IDs:\n{}'.format('\n'.join([str((i, each_id)) for i, each_id in enumerate(selected_ids)])))
        logger.info('Unique {} found in selection: {}'.format(id_field, num_selection_ids))

    stats_fields_dict = {'cloudcover': [max_cc],
                         'acq_time':   [min_year, max_year],
                         'off_nadir':  [max_off_nadir],
                         'spec_type':  [spec_type]}
    stats_fields = [fld for fld in arcpy.ListFields(selection)
                    if fld.name in stats_fields_dict.keys() and any(stats_fields_dict[fld.name])]

    if count != 0:
        for fld in stats_fields:
            logger.debug('Calculating summary statistics for field: {}'.format(fld.name))
            if fld.type in ['Integer', 'Double', 'SmallInteger', 'Date']:
                fld_min = min([row[0] for row in arcpy.da.SearchCursor(selection, (fld.name), where_clause='{} IS NOT NULL'.format(fld.name))])
                fld_max = max([row[0] for row in arcpy.da.SearchCursor(selection, (fld.name), where_clause='{} IS NOT NULL'.format(fld.name))])
                logger.info('{} min: {}'.format(fld.name, fld_min))
                logger.info('{} max: {}'.format(fld.name, fld_max))
            elif fld.type == 'String':
                if fld.name == 'acq_time':
                    fld_min = min([datetime.datetime.strptime(row[0][:10], '%Y-%m-%d') for row in arcpy.da.SearchCursor(selection, (fld.name), where_clause='{} IS NOT NULL'.format(fld.name))])
                    fld_max = max([datetime.datetime.strptime(row[0][:10], '%Y-%m-%d') for row in arcpy.da.SearchCursor(selection, (fld.name), where_clause='{} IS NOT NULL'.format(fld.name))])
                    logger.info('{} min: {}'.format(fld.name, fld_min))
                    logger.info('{} max: {}'.format(fld.name, fld_max))
                else:
                    fld_unique = set([row[0] for row in arcpy.da.SearchCursor(selection, (fld.name), where_clause='{} IS NOT NULL'.format(fld.name))])
                    logger.info('{} unique: {}'.format(fld.name, fld_unique))

        if not dryrun:
            write_shp(selection, out_path)
        else:
            logger.info('Dryrun - skipping writing.')
    else:
        logger.info('No matching features found, skipping writing.')
