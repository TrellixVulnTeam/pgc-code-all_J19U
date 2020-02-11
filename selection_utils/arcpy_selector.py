# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import argparse
import logging.config
import os
import sys
import geopandas as gpd
from shapely.geometry import Point

import arcpy

from misc_utils.id_parse_utils import read_ids, pgc_index_path
from misc_utils.logging_utils import LOGGING_CONFIG, CustomError



imagery_index = pgc_index_path()
arcpy.env.overwriteOutput = True


def check_where(where):
    if where:
        where += ' AND '
    return where


def determine_input_type(selector_path):
    """
    Determines the type of selector provided (.shp or .txt)
    based on the extension.
    """
    ext = os.path.basename(selector_path).split('.')[1]
    
    return ext


def danco_connection(db, layer):
    arcpy.env.overwriteOutput = True

    # Local variables:
    arcpy_cxn = "C:\\dbconn\\arcpy_cxn"
    #arcpy_footprint_MB_sde = arcpy_cxn

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
    """
    Creates a layer of a placename from danco acan DB.
    """
#    place_name_formats = ','.join([place_name, place_name.upper(), place_name.lower(), place_name.title()])
#    where = """Gazatteer Name IN ({})""".format(place_name_formats)
    where = """gaz_name = '{}'""".format(place_name)
    place_name_layer_p = danco_connection('acan', 'ant_gnis_pt')
    aoi = arcpy.MakeFeatureLayer_management(place_name_layer_p, out_layer='place_name_lyr',
                                            where_clause=where)
    arcpy.CopyFeatures_management(aoi, selector_path)

    return selector_path


def create_points(coords, shp_path):
    """
    Creates a point shapefile from long, lat pairs.
    """
    logger.info('Creating point shapefile from long, lat pairs(s)...')
    points = [Point(float(pair.split(',')[0]), float(pair.split(',')[1])) for pair in coords]
    gdf = gpd.GeoDataFrame(geometry=points, crs={'init':'epsg:4326'})
    gdf.to_file(shp_path)


def select_footprints(selector_path, input_type, imagery_index, overlap_type, search_distance, id_field):
    if input_type == 'shp':
        if not id_field:
            logger.info('Loading index...')
            idx_lyr = arcpy.MakeFeatureLayer_management(imagery_index)
            logger.info('Loading AOI...')
            aoi_lyr = arcpy.MakeFeatureLayer_management(selector_path)
            logger.info('Making selection...')
            selection = arcpy.SelectLayerByLocation_management(idx_lyr, 
                                                               overlap_type, 
                                                               aoi_lyr, 
                                                               selection_type="NEW_SELECTION", 
                                                               search_distance=search_distance)
        else:
            logger.info('Reading in IDs...')
            try:
                ids = read_ids(selector_path, field=id_field)
            except KeyError:
                ids = read_ids(selector_path, field=''.join(id_field.split('_')).lower())
            logger.info('{} IDs found.'.format(len(ids)))
            logger.debug('IDs: {}'.format(ids))
            ids_str = str(ids)[1:-1]
            where = """{} IN ({})""".format(id_field, ids_str)
            logger.debug('Where clause for ID selection: {}'.format(where))
            logger.info('Making selection...')
            selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)

    elif input_type == 'txt':
        ## Initial selection by id
        logger.info('Reading in IDs...')
        ids = read_ids(selector_path)
        logger.info('{} IDs found.'.format(len(ids)))
        logger.debug('IDs: {}'.format(ids))
        ids_str = str(ids)[1:-1]
        where = """{} IN ({})""".format(id_field, ids_str)
        logger.debug('Where clause for ID selection: {}'.format(where))
        logger.info('Making selection...')
        selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)
        # if arcpy.GetCount_management(selection).GetOutput(0) == 0:
            # try removing underscore and making lowercase
            # logger.debug('No results found, trying alternative format for id_field.')
            # where = """{} IN ({})""".format(''.join(id_field.split('_')).lower(), ids_str)
    result = arcpy.GetCount_management(selection)
    count = int(result.getOutput(0))
    logger.debug('Selected features: {}'.format(count))
        
    return selection


def select_dates(src, min_year, max_year, months):
    """
    Select by years and months
    """
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
    return out_shp


if __name__ == '__main__':
    ## Default arguments
    argdef_sensors          = ['QB01', 'IK01', 'GE01', 'WV01', 'WV02', 'WV03']
    argdef_prod_code        = ['M1BS', 'P1BS']
    argdef_min_year         = '1900'
    argdef_max_year         = '9999'
    argdef_months           = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    argdef_overlap_type     = 'INTERSECT'
    argdef_search_distance  = 0
    argdef_place_name       = None
    argdef_coordinate_pairs = None
    # argdef_id_field         = 'CATALOG_ID'
    argdef_id_field         = None
    

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('out_path', type=os.path.abspath, help='Path to write selection shp file.')
    parser.add_argument('-s', '--selector_path', type=str, 
                        help='''The path to the selector to use. This can be an AOI .shp file or 
                        .txt file of ids. If .txt, --id_field is required. If providing coordinates 
                        or placename, the path to write the created AOI shapefile to.''')
    parser.add_argument('--id_field', type=str, default=argdef_id_field,
                        help='''If using a .txt file of ids for the selection, specify here the 
                        type of ids in the .txt.: 
                        e.g.: CATALOG_ID, SCENE_ID, etc.''')
    parser.add_argument('--secondary_selector', type=os.path.abspath,
                        help='Path to an AOI layer to combine with an initial ID selection.')
    parser.add_argument('--prod_code', type=str, default=argdef_prod_code,
                        help='Prod code to select. E.g. P1BS, M1BS')
    parser.add_argument('--sensors', nargs='+', default=argdef_sensors,
                        help='Sensors to include.')
    parser.add_argument('--min_year', type=str, default=argdef_min_year, 
                        help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, default=argdef_max_year,
                        help='Latest year to include')
    parser.add_argument('--months', nargs='+', 
                        default=argdef_months,
                        help='Months to include. E.g. 01 02 03')
    parser.add_argument('--max_cc', type=int, help='Max cloudcover to include.')
    parser.add_argument('--max_off_nadir', type=int, help='Max off_nadir angle to include')
    parser.add_argument('--overlap_type', type=str, default=argdef_overlap_type,
                        help='''Type of select by location to perform. Must be one of:
                            the options available in ArcMap. E.g.: 'INTERSECT', 'WITHIN',
                            'CROSSED_BY_OUTLINE_OF', etc.''')
    parser.add_argument('--search_distance', type=str, default=argdef_search_distance,
                        help='''Search distance for overlap_types that support.
                        E.g. "10 Kilometers"''')
    parser.add_argument('--coordinate_pairs', nargs='*', default=argdef_coordinate_pairs,
                        help='Longitude, latitude pairs. x1,y1 x2,y2 x3,y3, etc.' )
    parser.add_argument('--place_name', type=str, default=argdef_place_name,
                        help='Select by Antarctic placename from acan danco DB.')
    parser.add_argument('-v', '--verbose', action='store_true',
                         help='Set logging level to DEBUG.')

    args = parser.parse_args()


    if args.verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'
    logging.config.dictConfig(LOGGING_CONFIG(handler_level))
    logger = logging.getLogger(__name__)
    
    
    out_path = args.out_path
    selector_path = args.selector_path
    id_field = args.id_field
    secondary_selector = args.secondary_selector
    prod_code = args.prod_code
    sensors = args.sensors
    min_year = args.min_year
    max_year = args.max_year
    months = args.months
    max_cc = args.max_cc
    max_off_nadir = args.max_off_nadir
    overlap_type = args.overlap_type
    search_distance = args.search_distance
    coordinate_pairs = args.coordinate_pairs
    place_name = args.place_name


    ## If coordinate pairs create shapefile
    if coordinate_pairs:
        logger.info('Using coordinate pairs:\n{}'.format(coordinate_pairs))
        coordinate_pairs = [c.strip("'") for c in coordinate_pairs]
        create_points(coordinate_pairs, selector_path)

    ## If place name provided, use as AOI layer
    if place_name is not None: 
        place_name_AOI(place_name, selector_path)


    ## Inital selection by location or ID
    logger.info('Making selection...')
    selection = select_footprints(selector_path=selector_path,
                                  input_type = determine_input_type(selector_path),
                                  imagery_index=imagery_index,
                                  overlap_type=overlap_type,
                                  search_distance=search_distance,
                                  id_field=id_field)
#                                      prod_code=prod_code)
    if secondary_selector:
        aoi_lyr = arcpy.MakeFeatureLayer_management(secondary_selector)
        selection = arcpy.SelectLayerByLocation_management(selection,
                                                           overlap_type,
                                                           aoi_lyr,
                                                           selection_type="SUBSET_SELECTION",
                                                           search_distance=search_distance)
    
    ## Initialize an empty where clause
    where = ''
    ## CC20 if specified
    if max_cc:
        where = check_where(where)
        where += """(cloudcover <= {})""".format(max_cc)
    ## PROD_CODE if sepcified
    if prod_code:
        where = check_where(where)
        prod_code_str = str(prod_code)[1:-1]
        where += """(prod_code IN ({}))""".format(prod_code_str)
    ## Selection by sensor if specified
    if sensors:
        where = check_where(where)
        sensors_str = str(sensors)[1:-1]
        where += """(sensor IN ({}))""".format(sensors_str)
    ## Time selection
    if min_year!=argdef_min_year or max_year!=argdef_max_year or months!=argdef_months:
        where = check_where(where)
        year_sql = """ "acq_time" > '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
        month_terms = [""" "acq_time" LIKE '%-{}-%'""".format(month) for month in months]
        month_sql = " OR ".join(month_terms)
        where += """({}) AND ({})""".format(year_sql, month_sql)
    if max_off_nadir:
        where = check_where(where)
        off_nadir_sql = """(off_nadir < {})""".format(max_off_nadir)
        where += off_nadir_sql
    logger.debug('Where clause for feature selection: {}'.format(where))
    
    
    selection = arcpy.MakeFeatureLayer_management(selection, where_clause=where)

    ## Selection by date if specified
    selection = select_dates(selection, min_year=min_year, max_year=max_year, months=months)

    # Print number of selected features
    result = arcpy.GetCount_management(selection)
    count = int(result.getOutput(0))
    logger.info('Selected features: {}'.format(count))
    if count != 0:
        write_shp(selection, out_path)
    else:
        logger.info('No matching features found, skipping writing.')
