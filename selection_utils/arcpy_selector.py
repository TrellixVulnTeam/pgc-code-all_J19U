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
from arcpy_utils.arcpy_utils import get_unique_ids, get_count
from arcpy_utils.arcpy_join import table_join
from misc_utils.logging_utils import create_logger

arcpy.env.qualifiedFieldNames = False

footprint_sde = r'\\files.umn.edu\pgc\trident\db\danco\footprint.sde'
# danco_catid_table = 'footprint.sde.pgc_imagery_catalogids'
fp_pgc_stereo_tbl = 'footprint.sde.pgc_imagery_catalogids_stereo'
dg_stereo_catids_tbl = 'footprint.sde.dg_imagery_index_stereo'
fp_pgc_stereo_tbl_abs = os.path.join(footprint_sde, fp_pgc_stereo_tbl)
dg_stereo_catids_tbl_abs = os.path.join(footprint_sde, dg_stereo_catids_tbl)

acan_sde = r'\\files.umn.edu\pgc\trident\db\danco\acan.sde'
ant_placename_tbl = 'ant_gnis_pt'
ant_placename_tbl_abs = os.path.join(acan_sde, ant_placename_tbl)


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


def log_where(where, max_length=2000, slice=150):
    if len(where) < max_length:
        logger.debug('Where: {}'.format(where))
    else:
        logger.debug('Where (AND):')
        ands = where.split(' AND ')
        for statement in ands:
            if len(statement) < slice:
                logger.debug(statement)
            else:
                logger.debug('{} ... {}'.format(statement[:slice], statement[-slice:]))


def determine_input_type(selector, selector_field):
    """
    Determine the type of selector provided (.shp or .txt)
    based on the extension.
    """
    ext = os.path.basename(selector).split('.')[1]

    if ext in ['shp', 'geojson'] and not selector_field:
        input_type = 'location'
    else:
        input_type = 'ids'

    return input_type


def create_where(max_cc=None, prod_code=None, sensors=None,
                 min_x=None, max_x=None, min_y=None, max_y=None,
                 min_year=None, max_year=None, months=None,
                 max_off_nadir=None, spec_type=None,
                 status=None, stereo_only=None, omit_ids=None,
                 argdef_min_year=None, argdef_max_year=None, argdef_months=None):
    where = ''
    # CC20 if specified
    if max_cc:
        if max_cc > 1:
            logger.warning('Cloudcovers in MFP are specified as porportions from 0.0 - 1.0. '
                           'Converting {} to this scale.'.format(max_cc))
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
        year_sql = """ acq_time >= '{}-00-00' AND acq_time <= '{}-12-32'""".format(min_year, max_year)
        month_terms = [""" acq_time LIKE '%-{}-%'""".format(month) for month in months]
        month_sql = " OR ".join(month_terms)
        where += """({}) AND ({})""".format(year_sql, month_sql)
    if min_x:
        where = check_where(where)
        where += """(cent_long >= {})""".format(min_x)
    if max_x:
        where = check_where(where)
        where += """(cent_long <= {})""".format(max_x)
    if min_y:
        where = check_where(where)
        where += """(cent_lat >= {})""".format(min_y)
    if max_y:
        where = check_where(where)
        where += """(cent_lat <= {})""".format(max_y)
    if max_off_nadir:
        where = check_where(where)
        off_nadir_sql = """(off_nadir < {})""".format(max_off_nadir)
        where += off_nadir_sql
    if spec_type:
        where = check_where(where)
        spec_type_str = str(spec_type)[1:-1]
        spec_type_sql = """(spec_type IN ({}))""".format(spec_type_str)
        where += spec_type_sql
    if status:
        where = check_where(where)
        where += "(STATUS IN ({}))".format(str(status)[1:-1])
    if stereo_only:
        where = check_where(where)
        stereo_ids = get_unique_ids(dg_stereo_catids_tbl_abs, 'catalogid')
        stereo_where = "(CATALOG_ID IN ({}))".format(str(stereo_ids)[1:-1])
        where += stereo_where
    if omit_ids:
        where = check_where(where)
        where += "(CATALOG_ID NOT IN ({}))".format(str(omit_ids)[1:-1])

    log_where(where)

    return where


def place_name_AOI(place_name, selector):
    """Create a layer of a placename from danco acan DB."""
    where = """gaz_name = '{}'""".format(place_name)
    # place_name_layer_p = danco_connection('acan', 'ant_gnis_pt')
    aoi = arcpy.MakeFeatureLayer_management(ant_placename_tbl_abs, out_layer='place_name_lyr',
                                            where_clause=where)
    arcpy.CopyFeatures_management(aoi, selector)

    return selector


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


def select_footprints(selector, input_type, imagery_index, join_field=None,
                      overlap_type=None, search_distance=None, id_field=None,
                      selector_field=None, sjoin=False, where=None):
    """Select footprints from MFP given criteria"""
    if input_type == 'location' and not selector_field:
        selection = select_by_location(aoi_path=selector, overlap_type=overlap_type,
                                       imagery_index=imagery_index, search_distance=search_distance,
                                       where=where)
        if sjoin:
            logger.info("Performing spatial join to transfer aoi fields to selection.")
            selection = arcpy.SpatialJoin_analysis(selection, selector, r'memory\sjoin')
    else:
        selection = select_by_id(selector=selector, imagery_index=imagery_index, id_field=id_field,
                                 selector_field=selector_field, where=where, join_field=join_field)

        count = get_count(selection)
        logger.debug('Selected features: {}'.format(count))
        if count == 0:
            logger.warning('No features found, exiting...')
            sys.exit()

    return selection


def select_by_id(selector, imagery_index, id_field='CATALOG_ID', where=None,
                 selector_field=None, join_field=None):
    """Select scene footprints from the master footprint by ID"""
    logger.info('Selecting by IDs...')
    # Initial selection by id
    if type(selector) == str:
        logger.info('Reading in IDs from: {}'.format(os.path.basename(selector)))
        # ids = sorted(read_ids(selector, field=selector_field))
        if selector.endswith('.txt'):
            ids = read_ids(selector)
        else:
            ids = get_unique_ids(table=selector, field=selector_field)

    else:
        ids = selector
    unique_ids = set(ids)
    logger.info('Total source IDs found: {}'.format(len(ids)))
    logger.info('Unique source IDs found: {}'.format(len(unique_ids)))
    logger.debug('IDs:\n{}'.format('\n'.join(ids)))

    ids_str = str(ids)[1:-1]
    where = check_where(where)
    where += """({} IN ({}))""".format(id_field, ids_str)
    logger.debug('Where clause for ID selection: {}\n'.format(where))

    logger.info('Making selection by IDs...')
    selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)

    if join_field:
        selection = table_join(layer=selection, layer_field=id_field,
                               join_table=selector, join_field=join_field,)

    selected_ids = set([row[0] for row in arcpy.da.SearchCursor(selection, [id_field])])
    logger.info('Selected IDs: {}'.format(len(selected_ids)))
    missing_ids = unique_ids - selected_ids
    logger.info('Missing IDs:\n{}'.format('\n'.join(missing_ids)))
    logger.info('Missing IDs: {}'.format(len(missing_ids)))

    return selection


def select_by_location(aoi_path, imagery_index, overlap_type, search_distance, where=None):
    """Select scene footprints from master footprint by location with AOI"""
    logger.info('Performing selection by location...')
    logger.info('Loading index: {}'.format(imagery_index))
    log_where(where)
    idx_lyr = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)
    logger.info('Loading AOI: {}'.format(aoi_path))
    aoi_lyr = arcpy.MakeFeatureLayer_management(aoi_path)
    logger.info('Making selection by location...')
    selection = arcpy.SelectLayerByLocation_management(idx_lyr,
                                                       overlap_type,
                                                       aoi_lyr,
                                                       selection_type="NEW_SELECTION",
                                                       search_distance=search_distance)

    return selection


def select_dates(src, min_year, max_year, months):
    """Select by years and months"""
    year_sql = """ "acq_time" >= '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
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
    count = get_count(selection)
    logger.info('Features in shapefile: {:,}'.format(count))
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
    argdef_status           = ['online', 'tape']

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    search_type_group = parser.add_argument_group('Search Type Specification')
    attributes_group = parser.add_argument_group('Attribute Selection')
    search_group = parser.add_argument_group('Search Parameters')
    misc_group = parser.add_argument_group('Misc.')

    parser.add_argument('out_path', type=os.path.abspath,
                        help='Path to write selection shp file.')

    # Specifying search type (IDs, location)
    search_type_group.add_argument('-s', '--selector', type=os.path.abspath,
                                   help='''The path to the selector to use. 
                                   This can be an AOI .shp file or .txt file 
                                   of ids. If .txt, --id_field is required. 
                                   If providing coordinates or placename, 
                                   the path to write the created AOI shapefile to.''')
    search_type_group.add_argument('--ids', type=str, nargs='+',
                                   help="""Alternatively, provide IDs seperated by spaces 
                                   to select. Field will be id_field in this case.""")
    search_type_group.add_argument('--id_field', type=str, default=argdef_id_field,
                                   help='''If using a .txt file of ids for the selection, 
                                   specify here the type of ids in the .txt, i.e. the field
                                   in the master footprint to select by.: 
                                   e.g.: CATALOG_ID, SCENE_ID, etc.''')
    search_type_group.add_argument('--selector_field', type=str,
                                   help="""If selector is shp, and select by ID desired, 
                                   the field name to pull IDs from.""")
    search_type_group.add_argument('--join_field', type=str,
                                   help='Field in selector to join selector to MFP selection.')
    search_type_group.add_argument('--secondary_selector', type=os.path.abspath,
                                   help='Path to an AOI layer to combine with an initial ID selection.')
    search_type_group.add_argument('--coordinate_pairs', nargs='*', default=argdef_coordinate_pairs,
                                   help='Longitude, latitude pairs. x1,y1 x2,y2 x3,y3, etc.')
    search_type_group.add_argument('--place_name', type=str, default=argdef_place_name,
                                   help='Select by Antarctic placename from acan danco DB.')

    # Attribute based arguments
    attributes_group.add_argument('--prod_code', type=str, nargs='+', default=argdef_prod_code,
                                  help='Prod code to select. E.g. P1BS, M1BS')
    attributes_group.add_argument('--sensors', nargs='+', default=argdef_sensors,
                                  help='Sensors to include. E.g. WV01 WV02')
    attributes_group.add_argument('--spec_type', nargs='+',
                                  help='spec_type to include. eg. SWIR Multispectral')
    attributes_group.add_argument('--min_year', type=str, default=argdef_min_year,
                                  help='Earliest year to include.')
    attributes_group.add_argument('--max_year', type=str, default=argdef_max_year,
                                  help='Latest year to include')
    attributes_group.add_argument('--months', nargs='+',
                                  default=argdef_months,
                                  help='Months to include. E.g. 01 02 03')
    attributes_group.add_argument('--min_x', type=float,
                                  help='Minimum longitude to include (centroid)')
    attributes_group.add_argument('--max_x', type=float,
                                  help='Maximum longitude to include (centroid)')
    attributes_group.add_argument('--min_y', type=float,
                                  help='Minimum latitude to include (centroid)')
    attributes_group.add_argument('--max_y', type=float,
                                  help='Maximum latitude to include (centroid)')
    attributes_group.add_argument('--max_cc', type=float, help='Max cloudcover to include.')
    attributes_group.add_argument('--max_off_nadir', type=int, help='Max off_nadir angle to include')
    attributes_group.add_argument('--status', nargs='+', default=argdef_status,
                                  help='Status: online, offline, tape.')

    # Search parameter arguments
    search_group.add_argument('--overlap_type', type=str, default=argdef_overlap_type, choices=argdef_overlap_type_choices,
                        help='''Type of select by location to perform. Must be one of:
                            the options available in ArcMap. E.g.: 'INTERSECT', 'WITHIN',
                            'CROSSED_BY_OUTLINE_OF', etc.''')
    search_group.add_argument('--search_distance', type=str, default=argdef_search_distance,
                        help='''Search distance for overlap_types that support.
                        E.g. "10 Kilometers"''')

    # Misc Args
    misc_group.add_argument('--sjoin', action='store_true',
                            help='Use to join attributes from an AOI layer. Useful for use with ir.py --opf')
    misc_group.add_argument('--stereo_only', action='store_true',
                            help='Select only stereo IDs (using footprint.pgc_imagery_catalogids_stereo')
    misc_group.add_argument('--omit_ids', type=os.path.abspath,
                            help='Path to text file of IDs to not include in final selection.')
    misc_group.add_argument('--override_defaults', action='store_true',
                            help="""Use this flag to not use any default attribute selection 
                            parameters: prod_code, sensors, spec_type, max_cc, max_off_nadir""")
    misc_group.add_argument('--dryrun', action='store_true',
                            help='Print information about selection, but do not write.')
    misc_group.add_argument('-v', '--verbose', action='store_true',
                            help='Set logging level to DEBUG.')

    args = parser.parse_args()

    # Logging
    if args.verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'
    logger = create_logger(__name__, 'sh', handler_level)

    # Parse args variables
    out_path = args.out_path
    selector = args.selector
    input_ids = args.ids
    id_field = args.id_field
    selector_field = args.selector_field
    join_field = args.join_field
    secondary_selector = args.secondary_selector
    sjoin = args.sjoin
    prod_code = args.prod_code
    sensors = args.sensors
    spec_type = args.spec_type
    min_year = args.min_year
    max_year = args.max_year
    months = args.months
    min_x = args.min_x
    max_x = args.max_x
    min_y = args.min_y
    max_y = args.max_y
    max_cc = args.max_cc
    max_off_nadir = args.max_off_nadir
    status = args.status
    stereo_only = args.stereo_only
    omit_ids_path = args.omit_ids
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
        create_points(coordinate_pairs, selector)

    # If place name provided, use as AOI layer
    if place_name is not None:
        place_name_AOI(place_name, selector)

    if selector:
        input_type = determine_input_type(selector, selector_field)
    elif input_ids:
        input_type = 'ids'
        selector = set(input_ids)
    logger.debug('Selection type: {}'.format(input_type))

    if omit_ids_path:
        omit_ids = read_ids(omit_ids_path)
    else:
        omit_ids = None

    where = create_where(max_cc=max_cc, prod_code=prod_code, sensors=sensors,
                         min_year=min_year, max_year=max_year, months=months,
                         max_off_nadir=max_off_nadir, spec_type=spec_type,
                         min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y,
                         status=status, stereo_only=stereo_only, omit_ids=omit_ids,
                         argdef_min_year=argdef_min_year, argdef_max_year=argdef_max_year,
                         argdef_months=argdef_months)

    selection = select_footprints(selector=selector, input_type=input_type,
                                  imagery_index=imagery_index, join_field=join_field,
                                  selector_field=selector_field,
                                  overlap_type=overlap_type, search_distance=search_distance,
                                  id_field=id_field, sjoin=sjoin, where=where)

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

    # Logging final selection statistics and writing
    # Print number of selected features
    count = get_count(selection)
    logger.info('Selected features: {:,}'.format(count))

    # Reporting number of unique IDs in final selction
    if id_field:
        with arcpy.da.SearchCursor(selection, [id_field]) as cursor:
            selected_ids = [row[0] for row in cursor]
            num_selection_ids = len(set(selected_ids))
        # TODO: This is not reporting the correct number of unique IDs
        logger.debug(
            'Selected IDs:\n{}'.format('\n'.join([str((i, each_id)) for i, each_id in enumerate(selected_ids)])))
        logger.info('Unique {} found in selection: {}'.format(id_field, num_selection_ids))

    # Stats about final selection
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
