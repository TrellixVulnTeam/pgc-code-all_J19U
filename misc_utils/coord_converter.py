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
    
    in_coord.replace('\xa0', ' ')
    # print(in_coord.split(' '))
    deg, minutes, seconds, direct = in_coord.split(' ')
    print(deg, minutes, seconds, direct)
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


def ddm_to_dd(in_coord, direct):
    '''takes in degrees, decimal minutes coordinate and returns decimal degrees'''
    in_coord = in_coord.strip()
    
    in_coord.replace('\xa0', ' ')
    # print(in_coord.split(' '))
    deg, n, minutes, direct = in_coord.split(' ')
    # print(deg, minutes, direct)
    dec_mins = float(minutes) / 60.
    # dec_seconds = float(seconds) / 3600
    dd = float(deg) + dec_mins
    pos_dirs = ['N', 'E']
    neg_dirs = ['S', 'W']
    if direct.upper() in pos_dirs:
        pass
    elif direct.upper() in neg_dirs:
        dd = -dd
    return dd


def conv_direction(in_coord):
    in_coord = in_coord.strip()
    in_coord.replace('\xa0', ' ')
    print(in_coord.split(' '))
    deg, minutes, seconds, direct = in_coord.split(' ')
    return direct


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=os.path.abspath, help='Path to csv to convert.')
    parser.add_argument('-cf', '--coordinate_format', 
                        type=str,
                        choices=['dms', 'ddm'],
                        default='dms',
                        help="""Format of input coordinates: 
                                dms: degrees, minutes, seconds
                                ddm: degrees, decimal minutes""")
    parser.add_argument('out_excel_path', type=os.path.abspath)
    parser.add_argument('-os', '--out_shapefile',
                        type=os.path.abspath,
                        help='Specify shapefile output path if desired.')
    parser.add_argument('-lat', '--latitude_column', 
                        type=str,
                        default='Latitude',
                        help='Name of latitude column.')
    parser.add_argument('-lon', '--longitude_column', 
                        type=str,
                        default='Longitude',
                        help='Nmae of longitude column.')

    args = parser.parse_args()

    csv = args.csv
    coord_format = args.coordinate_format
    lat = args.latitude_column
    lon = args.longitude_column
    out_excel = args.out_excel_path
    out_shp = args.out_shapefile
    # sites = pd.read_csv(args.csv, encoding="ISO-8859-1")
    if csv[-3:] == 'csv':
        sites = pd.read_csv(csv)
    else:
        sites = pd.read_excel(csv)

    sites = remove_symbols(sites)

    print('Converting...')
    coord_cols = [lat, lon]
    for col in coord_cols:
        col_name = '{}_DD'.format(col)
        sites[col_name] = sites[col]
        # col_dir = '{} Direction'.format(col[:3])
        sites['{}_Dir'.format(col)] = sites.apply(lambda x: conv_direction(x[col_name]), axis=1)
        if coord_format == 'dms':
            sites[col_name] = sites.apply(lambda x: dms_to_dd(x[col_name], x['{}_Dir'.format(col)]), axis=1)
        elif coord_format == 'ddm':
            sites[col_name] = sites.apply(lambda x: ddm_to_dd(x[col_name], x['{}_Dir'.format(col)]), axis=1)
        else:
            print('Unrecognized coordinate format: {}'.format(coord_format))
            print('Must be one of: "dms", "ddm".')

    print('Writing to excel: {}'.format(out_excel))
    sites.to_excel(out_excel)
    
    if out_shp:
        import geopandas as gpd
        from shapely.geometry import Point
        
        geometry = [Point(x, y) for x, y in zip(sites['{}_DD'.format(lon)], sites['{}_DD'.format(lat)])]
        points = gpd.GeoDataFrame(sites, crs='epsg:4326', geometry=geometry)
        print('Writing to shapefile: {}'.format(out_shp))
        points.to_file(out_shp)

# csv = r'V:\pgc\data\scratch\jeff\ms\shapefile\supp_tks_loc\bjones_thaw_Slump_Locations\Thaw_Slump_Locations\Kokelj_et_al_2017_Thaw_Slumps_2017106.xlsx '
# sites = pd.read_excel(csv)
# # print(sites)

# sites = remove_symbols(sites)
# #
# coord_cols = ['Latitude', 'Longitude']
# for col in coord_cols:
#     col_name = '{}_DD'.format(col)
#     sites[col_name] = sites[col]
#     # col_dir = '{} Direction'.format(col[:3])
#     sites['{}_Dir'.format(col)] = sites.apply(lambda x: conv_direction(x[col_name]), axis=1)
#     # sites[col_name] = sites.apply(lambda x: dms_to_dd(x[col_name], x['{}_Dir'.format(col)]), axis=1)
#     sites[col_name] = sites.apply(lambda x: ddm_to_dd(x[col_name], x['{}_Dir'.format(col)]), axis=1)

# print(sites)
# sites.to_excel(r'V:\pgc\data\scratch\jeff\ms\shapefile\supp_tks_loc\bjones_thaw_Slump_Locations\Thaw_Slump_Locations\Kokelj_et_al_2017_Thaw_Slumps_2017106_coord_conv.xls')