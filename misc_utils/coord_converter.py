# -*- coding: utf-8 -*-
"""
Created on Fri Jan 18 09:25:18 2019

@author: disbr007
"""

import argparse
import os
import pandas as pd


def remove_symbols(coords):
    # If string assume to be path to csv/excel
    if type(coords) == str:
        coords = pd.read_csv(coords, encoding="ISO-8859-1")
    # Else assume DF
    coords = coords.replace('°', ' ', regex=True)
    coords = coords.replace('°', ' ', regex=True)
    coords = coords.replace('º', ' ', regex=True)
    coords = coords.replace('°', ' ', regex=True)
    coords = coords.replace('"', ' ', regex=True)
    coords = coords.replace("'", ' ', regex=True)
#    coords = coords.replace("  ", ' ', regex=True)
#    coords.columns = coords.columns.str.replace(' ', '')
    return coords

def coord_conv(in_coord, coord_type):
    if coord_type == 'DDM': # D DM N
        deg, dec_min, direction = in_coord.split(' ')
        dec_degrees = float(deg) + float(dec_min)/60
    elif coord_type == 'Dir DD':
        direction = in_coord.split(' ')[0]
        dec_degrees = float(in_coord.split(' ')[1])
    else:
        dec_degrees = None
    if direction in ('S', 'W'):
        dec_degrees = -dec_degrees
    elif direction in ('N', 'E'):
        dec_degrees = dec_degrees
    else:
        dec_degrees = None
    return dec_degrees

def dms_to_dd(in_coord, direct):
    '''takes in degrees, minutes, and seconds coordinate and returns decimal degrees'''
    in_coord = in_coord.strip()
    print(in_coord.split(' '))
    deg, minutes, seconds, direct = in_coord.split(' ')
    dec_mins = float(minutes) / 60.
    dec_seconds = float(seconds) / 3600
    dd = float(deg) + dec_mins + dec_seconds
    pos_dirs = ['N', 'E']
    neg_dirs = ['S', 'W']
    if direct.upper() in pos_dirs:
        pass
    elif direct.upper() in neg_dirs:
        dd = -dd
    return dd

def conv_direction(in_coord):
    in_coord = in_coord.strip()
    print(in_coord.split(' '))
    deg, minutes, seconds, direct = in_coord.split(' ')
    return direct


# if __name__ == '__main__':
#     parser = argparse.Argument_Parser()
#     parser.add_argument('csv', type=str,help='Path to csv to convert.')

#     args = parser.parse_args()



excel_path = r"C:\temp\sites_dms.csv"
sites = pd.read_csv(excel_path, encoding="ISO-8859-1")

sites = remove_symbols(sites)
#
coord_cols = ['Latitude', 'Longitude']
for col in coord_cols:
    col_name = '{}_DD'.format(col)
    sites[col_name] = sites[col]
    # col_dir = '{} Direction'.format(col[:3])
    sites['{}_Dir'.format(col)] = sites.apply(lambda x: conv_direction(x[col_name]), axis=1)
    sites[col_name] = sites.apply(lambda x: dms_to_dd(x[col_name], x['{}_Dir'.format(col)]), axis=1)
  

out_excel_path = os.path.join(os.path.dirname(excel_path), '{}_converted.csv'.format(os.path.splitext(os.path.basename(excel_path))[0]))
# excel_writer = pd.ExcelWriter(out_excel_path)
sites.to_csv(out_excel_path)
# excel_writer.save()