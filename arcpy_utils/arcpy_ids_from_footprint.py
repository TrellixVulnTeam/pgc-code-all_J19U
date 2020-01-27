# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 12:17:08 2019

@author: disbr007
"""

import arcpy
import argparse
import os
from tqdm import tqdm


def get_field_values(fc, field, unique):
    '''
    Returns a list of all values in a given field
    fc: feature class
    field: field of interest
    unique: if True, returns a set of the values
    '''
    ## Set up arcpy cursor and list to store ids
    cursor = arcpy.SearchCursor(fc)
    ids = []
    num_rows = int(arcpy.GetCount_management(fc)[0])
    print(num_rows)
#    pbar = tqdm(total=10000)
    with tqdm(total=num_rows) as pbar:
        for row in cursor:
            ids.append(row.getValue(field))
            pbar.update()
        if unique == True:
            ids = list(set(ids))
    
    return ids


def write_ids(ids, out_path, header=None):
    with open(out_path, 'w') as f:
        if header:
            f.write('{}\n'.format(header))
        for each_id in ids:
            f.write('{}\n'.format(each_id))


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('feature_class', type=str, help='Path to feature class containing field of interest')
    parser.add_argument('field', type=str, help='Field in feature class.')
    parser.add_argument('out_path', type=os.path.abspath, help='Path to write ids to.')
    parser.add_argument('--unique', '-u', action='store_true', help='Use flag to return only unique ids (no duplicates)')
    
    args = parser.parse_args()
    
    ids = get_field_values(args.feature_class, args.field, unique=args.unique)
    write_ids(ids, args.out_path)