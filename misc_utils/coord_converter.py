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


excel_path = r"E:\disbr007\UserServicesRequests\tasking_requests\Dial_PGC_Tasking_Request_Table_2018.xlsx"

coords = pd.read_excel(excel_path, encoding='utf-8', sheet_name = "Targets")
coords = coords.replace('°', '', regex=True)
coords = coords.replace('"', '', regex=True)

coord_cols = ['Latitude (decimal degrees)', 'Longitude (decimal degrees)']
for col in coord_cols:
    col_name = '{} DD'.format(col[:3])
    col_dir = '{} Direction'.format(col[:3])
    coords[col_name] = coords.apply(lambda x: coord_conv(x[col], 'Dir DD'), axis=1)
   

out_excel_path = os.path.join(os.path.dirname(excel_path), '{}_converted.xls'.format(os.path.splitext(os.path.basename(excel_path))[0]))
excel_writer = pd.ExcelWriter(out_excel_path)
coords.to_excel(excel_writer, 'coords', index=True)
excel_writer.save()