# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import argparse
import logging
import os
import sys
import geopandas as gpd
from shapely.geometry import Point

import arcpy

from id_parse_utils import read_ids


#### Logging setup
# create logger
logger = logging.getLogger('arcpy-selector')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


try:
    sys.path.insert(0, r'C:\pgc-code-all\misc_utils')
    from id_parse_utils import pgc_index_path
    imagery_index = pgc_index_path()
except ImportError:
    imagery_index = r'C:\pgc_index\pgcImageryIndexV6_2019aug28.gdb\pgcImageryIndexV6_2019aug28'
    logger.info('Could not load updated index. Using last known path: {}'.format(imagery_index))

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
#    logge.info(where)
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
    gdf.to_file(shp_path, driver='ESRI Shapefile')



def select_footprints(selector_path, input_type, imagery_index, overlap_type, search_distance):
    if input_type == 'shp':
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
    
    elif input_type == 'txt':
        ## Initial selection by id
        ids = read_ids(selector_path)
        ids_str = str(ids)[1:-1]
        where = """{} IN ({})""".format(id_field, ids_str)
        logger.debug('Where clause for ID selection: {}'.format(where))
        selection = arcpy.MakeFeatureLayer_management(imagery_index, where_clause=where)
        
        result = arcpy.GetCount_management(selection)
        count = int(result.getOutput(0))
        logger.debug('Selected features by ID: {}'.format(count))
        
    return selection


#def select_dates(src, min_year, max_year, months):
#    """
#    Select by years and months
#    """
#    year_sql = """ "acq_time" > '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
#    month_terms = [""" "acq_time" LIKE '%-{}-%'""".format(month) for month in months]
#    month_sql = " OR ".join(month_terms)
#    sql = """({}) AND ({})""".format(year_sql, month_sql)

    ## Faster by far than SelectByAttributes
#    selection = arcpy.MakeFeatureLayer_management(src, where_clause=sql)
#    return selection


def write_shp(selection, out_path):
    logger.info('Creating shapefile of selection...')
    out_shp = arcpy.CopyFeatures_management(selection, out_path)
    logger.info('Shapefile of selected features created at: {}'.format(out_path))
    return out_shp


if __name__ == '__main__':
    ## Default arguments
    argdef_prod_code = ['M1BS', 'P1BS']
    argdef_min_year = '1900'
    argdef_max_year = '9999'
    argdef_months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    argdef_overlap_type = 'INTERSECT'
    argdef_search_distance = 0
    argdef_place_name = None
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('out_path', type=os.path.abspath, help='Path to write selection shp file.')
    parser.add_argument('-s', '--selector_path', type=str, 
                        help='''The path to the selector to use. This can be an AOI .shp file or 
                        .txt file of ids. If .txt, --id_field is required. If providing coordinates 
                        or placename, the path to write the created AOI shapefile to.''')
    parser.add_argument('--id_field', type=str,
                        help='''If using a .txt file of ids for the selection, specify here the 
                        type of ids in the .txt.: 
                        e.g.: CATALOG_ID, SCENE_ID, etc.''')
    parser.add_argument('--prod_code', type=str, default=argdef_prod_code,
                        help='Prod code to select. E.g. P1BS, M1BS')
    parser.add_argument('--sensors', nargs='+', default=['IK01', 'GE01', 'WV01', 'WV02', 'WV03'],
                        help='Sensors to include.')
    parser.add_argument('--min_year', type=str, default=argdef_min_year, 
                        help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, default=argdef_max_year,
                        help='Latest year to include')
    parser.add_argument('--months', nargs='+', 
                        default=argdef_months,
                        help='Months to include. E.g. 01 02 03')
    parser.add_argument('--max_cc', type=int, help='Max cloudcover to include.')
    parser.add_argument('--overlap_type', type=str, default=argdef_overlap_type,
                        help='''Type of select by location to perform. Must be one of:
                            the options available in ArcMap. E.g.: 'INTERSECT', 'WITHIN',
                            'CROSSED_BY_OUTLINE_OF', etc. Default = 'INTERSECT' ''')
    parser.add_argument('--search_distance', type=str, default=argdef_search_distance,
                        help='''Search distance for overlap_types that support. Default = 0
                        E.g. "10 Kilometers"''')
    parser.add_argument('--coordinate_pairs', nargs='*', 
                        help='Longitude, latitude pairs. x1,y1 x2,y2 x3,y3, etc.' )
    parser.add_argument('--place_name', type=str, default=argdef_place_name,
                        help='Select by Antarctic placename from acan danco DB.')

    args = parser.parse_args()

    out_path = args.out_path
    selector_path = args.selector_path
    id_field = args.id_field
    prod_code = args.prod_code
    sensors = args.sensors
    min_year = args.min_year
    max_year = args.max_year
    months = args.months
    max_cc = args.max_cc
    overlap_type = args.overlap_type
    search_distance = args.search_distance
    coordinate_pairs = args.coordinate_pairs
    place_name = args.place_name


    ## If coordinate pairs create shapefile
    if coordinate_pairs:
        create_points(coordinate_pairs, selector_path)

    ## If place name provided, use as AOI layer
    if place_name: 
        place_name_AOI(place_name, selector_path)


    ## Inital selection by location or ID
    selection = select_footprints(selector_path=selector_path,
                                  input_type = determine_input_type(selector_path),
                                  imagery_index=imagery_index,
                                  overlap_type=overlap_type,
                                  search_distance=search_distance)
#                                      prod_code=prod_code)
    
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
    logger.info('Where clause for feature selection: {}'.format(where))
    
    
    selection = arcpy.MakeFeatureLayer_management(selection, where_clause=where)

#    ## Selection by date if specified
#    selection = select_dates(selection, min_year=min_year, max_year=max_year, months=months)

    # Print number of selected features
    result = arcpy.GetCount_management(selection)
    count = int(result.getOutput(0))
    logger.info('Selected features: {}'.format(count))

    write_shp(selection, out_path)
