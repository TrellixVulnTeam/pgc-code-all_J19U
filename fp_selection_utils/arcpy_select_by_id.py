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
    imagery_index = r'E:\disbr007\UserServicesRequests\pgcImageryIndexV6_2019jan12.gdb\pgcImageryIndexV6_2019jan12'
    selection = arcpy.SelectLayerByAttribute_management(imagery_index, "NEW_SELECTION", sql)
    return selection

def select_footprints_by_location(aoi):
    imagery_index = r'E:\disbr007\UserServicesRequests\pgcImageryIndexV6_2019jan12.gdb\pgcImageryIndexV6_2019jan12'
    aoi_lyr = arcpy.MakeFeatureLayer_management(aoi)
    selection = arcpy.SelectLayerByLocation_management(imagery_index, "INTERSECT", aoi_lyr, selection_type="NEW_SELECTION")
    return selection
    
def write_shp(selection, txt_file):
    project_path = os.path.dirname(txt_file)
    out_shp_path = os.path.join(project_path, 'selected_ids.shp')
    out_shp = arcpy.CopyFeatures_management(selection, out_shp_path)
    print('Shapefile of selected features created at: {}'.format(out_shp_path))
    return out_shp

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('selector', type=str, 
                        help='''The file to use to select features. This can be a shp file, which results in a 
                        SelectByLocation, or a .txt file containing one catalog ID per line.''')
    args = parser.parse_args()
    selector = args.selector
    ext = os.path.splitext(selector)[1]
    if ext == '.txt':
        ids = read_ids(selector)
        selection = select_footprints_by_attribute(ids)
    elif ext == '.shp':
        selector = select_footprints_by_location(selector)
    else:
        err = 'Selector filetype not recognized: {}'.format(selector)
        sys.exit(err)
    write_shp(selection, selector)

