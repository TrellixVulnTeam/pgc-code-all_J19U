# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import argparse
import sys

import arcpy


try:
    sys.path.insert(0, r'C:\pgc-code-all\misc_utils')
    from id_parse_utils import pgc_index_path
    imagery_index = pgc_index_path()
except ImportError:
    imagery_index = r'C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb\pgcImageryIndexV6_2019jun06'
    
arcpy.env.overwriteOutput = True


def select_footprints(aoi, imagery_index, overlap_type, search_distance):
#    imagery_index = pgc_index_path()
    print('Loading index...')
    idx_lyr = arcpy.MakeFeatureLayer_management(imagery_index)
    print('Loading AOI')
    aoi_lyr = arcpy.MakeFeatureLayer_management(aoi)
    selection = arcpy.SelectLayerByLocation_management(idx_lyr, overlap_type, aoi_lyr, selection_type="NEW_SELECTION")
    return selection


def select_dates(src, min_year=1990, max_year=2100, months=[0]):
    '''
    Select by years and months
    '''
    year_sql = """ "acq_time" > '{}-00-00' AND "acq_time" < '{}-12-32'""".format(min_year, max_year)
    month_terms = [""" "acq_time" LIKE '%-{}-%'""".format(month) for month in months]
    month_sql = " OR ".join(month_terms)
    sql = """({}) AND ({})""".format(year_sql, month_sql)
    
    ## Faster by far than SelectByAttributes
    selection = arcpy.MakeFeatureLayer_management(src, where_clause=sql)
    return selection
    

def write_shp(selection, out_path):
    print('Creating shapefile of selection...')
    out_shp = arcpy.CopyFeatures_management(selection, out_path)
    print('Shapefile of selected features created at: {}'.format(out_path))
    return out_shp



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('aoi_path', type=str, help='The path to the AOI shp file.')
    parser.add_argument('out_path', type=str, help='Path to write selection shp file.')
    parser.add_argument('--min_year', type=str, help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, help='Latest year to include')
    parser.add_argument('--months', nargs='+', help='Months to include. E.g. 01 02 03')
    parser.add_argument('--cc20', action='store_true', help='Use flag to specify cc20 or better.')
    parser.add_argument('--overlap_type', type=str, default='INTERSECT',
                        help='''Type of select by location to perform. Must be one of:
                            the options available in ArcMap. E.g.: 'INTERSECT', 'WITHIN',
                            'CROSSED_BY_OUTLINE_OF', etc. Default = 'INTERSECT' ''')
    parser.add_argument('--search_distance', type=int, default=0,
                        help='''Search distance for overlap_types that support. Default = 0''')
    
    
    args = parser.parse_args()
    
    aoi_path = args.aoi_path
    out_path = args.out_path
    min_year = args.min_year
    max_year = args.max_year
    months = args.months
    cc20 = args.cc20
    overlap_type = args.overlap_type
    search_distance = args.search_distance
    
    ## Inital selection by location
    selection = select_footprints(aoi_path, overlap_type, search_distance)
    
    ## CC20 if specified
    if cc20:
        selection = arcpy.MakeFeatureLayer_management(selection, where_clause="""cloudcover <= 0.20""")
    
    ## Selection by date if specified
    if None in (min_year, max_year, months):
        if min_year is None:
            min_year = '1900'
        if max_year is None:
            max_year = '2100'
        if months is None:
            months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        selection = select_dates(selection, min_year=min_year, max_year=max_year, months=months)
    
    
    write_shp(selection, out_path)

