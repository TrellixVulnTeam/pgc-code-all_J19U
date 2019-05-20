# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 09:53:14 2019

@author: disbr007
Select from index by list of ids
"""

import arcpy
import os, sys
import argparse

def read_ids(txt_file):
    ids = []
    with open(txt_file, 'r') as ids_file:
        content = ids_file.readlines()
        for line in content:
            ids.append(str(line).strip())
    return tuple(ids)

def select_footprints_by_attribute(ids):
    sql = """ "CATALOG_ID" IN {} """.format(ids)
    imagery_index = r"E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19.gdb\pgcImageryIndexV6_2019mar19"
    selection = arcpy.SelectLayerByAttribute_management(imagery_index, "NEW_SELECTION", sql)
    count = arcpy.GetCount_management(selection)
    print('Features selected: {}'.format(count))
    return selection

def select_footprints_by_location(aoi):
    imagery_index = r"E:\disbr007\pgc_index\pgcImageryIndexV6_2019mar19.gdb\pgcImageryIndexV6_2019mar19"
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
    parser.add_argument('out_name', type=str,
                        help='''The name of the shapefile to be written with the selection''')
    args = parser.parse_args()
    selector = args.selector
    out_name = args.out_name
    ext = os.path.splitext(selector)[1]
    if ext == '.txt':
        ids = read_ids(selector)
        selection = select_footprints_by_attribute(ids)
    elif ext == '.shp':
        selector = select_footprints_by_location(selector)
    else:
        err = 'Selector filetype not recognized: {}'.format(selector)
        sys.exit(err)
    write_shp(selection, selector, out_name)

