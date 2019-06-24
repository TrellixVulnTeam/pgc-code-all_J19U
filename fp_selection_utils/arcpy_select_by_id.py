# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import arcpy
import os, sys
import argparse


imagery_index = "C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb\pgcImageryIndexV6_2019jun06"

def read_ids(ids_file, sep=None, stereo=False):
    '''Reads ids from a variety of file types. Can also read in stereo ids from applicable formats
    Supported types:
        .txt: one per line, optionally with other fields after "sep"
        .dbf: shapefile's associated dbf    
    '''
    ids = []
    with open(ids_file, 'r') as f:
        content = f.readlines()
        for line in content:
            if sep:
                # Assumes id is first
                the_id = line.split(sep)[0]
                the_id = the_id.strip()
            else:
                the_id = line.strip()
            ids.append(the_id)
    ids_str = ''
    for i in ids:
        ids_str += "'{}',".format(i)
    ids_str = '(' + ids_str.rstrip(',') + ')'
    return ids_str


def select_footprints_by_attribute(field, ids):
    sql = """ {} IN {} """.format(field, ids)
    print(sql)
    selection = arcpy.SelectLayerByAttribute_management(imagery_index, "NEW_SELECTION", sql)
    count = arcpy.GetCount_management(selection)
    print('Features selected: {}'.format(count))
    return selection

def select_footprints_by_location(aoi):
    aoi_lyr = arcpy.MakeFeatureLayer_management(aoi)
    selection = arcpy.SelectLayerByLocation_management(imagery_index, "INTERSECT", aoi_lyr, selection_type="NEW_SELECTION")
    return selection
    
def write_shp(selection, selector, out_name):
    ## Get out path
    # If the selector is an absolute path, use the path provided
    if os.path.isabs(selector):
        project_path = os.path.dirname(selector)
    # If selector is relative path, use the current directory
    else:
        project_path = os.getcwd()
    # Path to write shapefile to
    out_shp_path = os.path.join(project_path, '{}.shp'.format(out_name))    
    out_shp = arcpy.CopyFeatures_management(selection, out_shp_path)
    print('Shapefile of selected features created at: {}'.format(out_shp_path))
    return out_shp

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('selector', type=str, 
                        help='''The file to use to select features. This can be a shp file, which results in a 
                        SelectByLocation, or a .txt file containing one catalog ID per line.''')
    parser.add_argument('field', type=str,
                        help='The field in the selector. E.g. CATALOG_ID, SCENE_ID, etc.')
    parser.add_argument('out_name', type=str,
                        help='''The name of the shapefile to be written with the selection''')
    args = parser.parse_args()
    selector = args.selector
    out_name = args.out_name
    ext = os.path.splitext(selector)[1]
    if ext == '.txt':
        ids = read_ids(selector)
        selection = select_footprints_by_attribute(args.field, ids)
    elif ext == '.shp':
        selector = select_footprints_by_location(selector)
    else:
        err = 'Selector filetype not recognized: {}'.format(selector)
        sys.exit(err)
    write_shp(selection, selector, out_name)

