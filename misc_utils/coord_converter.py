# -*- coding: utf-8 -*-
"""
Created on Fri Jan 18 09:25:18 2019

@author: disbr007
"""

import pandas as pd
import os

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

def dms_to_dd(in_coord):
    '''takes in degrees, minutes, and seconds coordinate and returns decimal degrees'''
    in_coord = in_coord.strip()
    print(in_coord.split(' '))
    deg, minutes, seconds = in_coord.split(' ')
    dec_mins = float(minutes) / 60.
    dec_seconds = float(seconds) / 3600
    dd = float(deg) + dec_mins + dec_seconds
    return dd


excel_path = r"C:\Users\disbr007\Downloads\Storg_sample_locations (1).xlsx"

coords = pd.read_excel(excel_path, encoding='utf-8', sheet_name = "Sheet1")
coords = coords.replace('°', ' ', regex=True)
coords = coords.replace('"', ' ', regex=True)
coords = coords.replace("'", ' ', regex=True)

coord_cols = ['N', 'E']
for col in coord_cols:
    col_name = '{} DD'.format(col[:3])
    col_dir = '{} Direction'.format(col[:3])
    coords[col_name] = coords.apply(lambda x: dms_to_dd(x[col]), axis=1)
   

out_excel_path = os.path.join(os.path.dirname(excel_path), '{}_converted.xls'.format(os.path.splitext(os.path.basename(excel_path))[0]))
excel_writer = pd.ExcelWriter(out_excel_path)
coords.to_excel(excel_writer, 'coords', index=True)
excel_writer.save()