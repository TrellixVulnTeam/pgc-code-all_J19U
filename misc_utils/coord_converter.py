# -*- coding: utf-8 -*-
"""
Created on Fri Jan 18 09:25:18 2019

@author: disbr007
"""

import argparse
import os
import pandas as pd
import re

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


def remove_symbols(coords):
    logger.debug('Removing any symbols....')
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


def split_combined(combined, splitters, coord_order):
    logger.debug('Splitting combined coordinates...')
    if coord_order in ['lat-lon-dir', 'lon-lat-dir']:
        m = -1
    elif coord_order in ['dir-lat-lon', 'dir-lon-lat']:
        m = 1
    splitters_string = ''.join(splitters)
    split = re.split('([{}])'.format(splitters_string), combined)
    coords = []
    for i, x in enumerate(split):
        x = x.strip()
        if x in splitters:
            if coord_order in ['lat-lon-dir', 'lon-lat-dir']:
                coords.append(split[i+m].strip() + ' ' + x)
            elif coord_order in ['dir-lat-lon', 'dir-lon-lat']:
                coords.append(x + ' ' + split[i+m].strip())
            
    if coord_order in ['lat-lon-dir', 'dir-lat-lon']:
        lat, lon = coords
    elif coord_order in ['lon-lat-dir', 'dir-lon-lat']:
        lon, lat = coords
        
    logger.debug((lat.strip(), lon.strip()))
    
    return (lat.strip(), lon.strip())


def coord_conv(in_coord, coord_format, coord_order):
    if coord_format == 'ddm': # D DM N
        if coord_order in ['lat-lon-dir', 'lon-lat-dir']:
            logger.debug(in_coord.split(' '))
            deg, dec_min, direction = in_coord.split(' ')
        elif coord_order in ['dir-lat-lon', 'dir-lon-lat']:
            direction, deg, dec_min = in_coord.split(' ')
        dec_degrees = float(deg) + float(dec_min)/60
    
    elif coord_format == 'dms':
        if coord_order in ['lat-lon-dir', 'lon-lat-dir']:
            direction = in_coord.split(' ')[-1]
            coords = in_coord[0:-1]
        elif coord_order in ['dir-lat-lon', 'dir-lon-lat']:
            direction = in_coord.split(' ')[0]
            coords = in_coord[1:]
        # dec_degrees = float(in_coord.split(' ')[1])
        dec_degrees = dms_to_dd(coords, direct=direction)
    
    elif coord_format == 'dd':
        dec_degrees = in_coord
        direction = None
    
    else:
        dec_degrees = None
    
    if direction in ('S', 'W'):
        dec_degrees = -dec_degrees
    elif direction in ('N', 'E'):
        dec_degrees = dec_degrees


    return dec_degrees


def dms_to_dd(in_coord, direct):
    '''takes in degrees, minutes, and seconds coordinate and returns decimal degrees'''
    in_coord = in_coord.strip()
        
    in_coord.replace('\xa0', ' ')
    logger.debug(in_coord)
    deg, minutes, seconds = [x for x in in_coord.split(' ') if x != '']
    logger.debug(deg, minutes, seconds, direct)
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
    # logger.debug(in_coord.split(' '))
    deg, n, minutes, direct = in_coord.split(' ')
    # logger.debug(deg, minutes, direct)
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
    logger.debug(in_coord.split(' '))
    deg, minutes, seconds, direct = in_coord.split(' ')
    
    return direct


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='Coordinate Converter',
                                      description="""Convert coordinates from a variety of formats
                                                    to decimal degrees. Optionally writing to 
                                                    shapefile.""")

    parser.add_argument('csv', type=os.path.abspath, help='Path to csv to convert.')
    parser.add_argument('-cf', '--coordinate_format', 
                        type=str,
                        choices=['dms', 'ddm', 'dd'],
                        default='dms',
                        help="""Format of input coordinates: 
                                dms: degrees, minutes, seconds
                                ddm: degrees, decimal minutes
                                dd : decimal degrees (just write to shape)""")
    parser.add_argument('out_excel_path', type=os.path.abspath)
    parser.add_argument('--combined_coords', type=str,
                        help="""Specify name of column with combined coordinates. Use either
                                this flag or -lat and -lon.""")
    parser.add_argument('--cc_splitters', nargs='+',
                        help="""Characters to split a combined coordinate column on.""")
    parser.add_argument('--coord_order', type=str, choices=['dir-lat-lon', 'dir-lon-lat',
                                                              'lat-lon-dir', 'lat-lon-dir'],
                        help="""If a combined column specified, the order of the combined
                                coordinates.""")
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
    combined_coords = args.combined_coords
    cc_splitters = args.cc_splitters
    coord_order = args.coord_order
    lat = args.latitude_column
    lon = args.longitude_column
    out_excel = args.out_excel_path
    out_shp = args.out_shapefile

    # DEBUGGING
    # csv = r'V:\pgc\data\scratch\jeff\deliverables\palmer_boating\chart_waypoints_mburns_dms_cleaned.xlsx'
    # out_excel = r'V:\pgc\data\scratch\jeff\deliverables\palmer_boating\chart_waypoints_mburns_dms_cleaned2.xlsx'
    # coord_format = 'dd'
    # # combined_coords = 'GPS location'
    # combined_coords = None
    # cc_splitters = None
    # coord_order = None
    # # cc_splitters = ['S', 'W']
    # # coord_order = 'dir-lat-lon'
    # out_shp = r'V:\pgc\data\scratch\jeff\deliverables\palmer_boating\chart_waypoints_mburns.shp'
    # lat = 'lat_DD'
    # lon = 'lon_DD'
    
    if csv[-3:] == 'csv':
        sites = pd.read_csv(csv)
    else:
        sites = pd.read_excel(csv)

    # Remove degree symbols, quotes
    sites = remove_symbols(sites)
    
    if combined_coords:
        lat = 'lat'
        lon = 'lon'
        sites[lat], sites[lon] = zip(*sites[combined_coords].apply(lambda x: split_combined(x, 
                                                                                            cc_splitters,
                                                                                            coord_order)))


    logger.debug('Converting...')
    coord_cols = [lat, lon]
    logger.debug('Columns: {}'.format(list(sites)))
    # print(list(sites))
    logger.debug('Coordinate columns: {}'.format(coord_cols))
    for col in coord_cols:
        col_name = '{}_DD'.format(col)
        sites[col_name] = sites[col]
        sites[col_name] = sites.apply(lambda x: coord_conv(x[col], 
                                                           coord_format=coord_format,
                                                           coord_order=coord_order), axis=1)
    logger.info('Writing to excel: {}'.format(out_excel))
    sites.to_excel(out_excel)
    
    if out_shp:
        import geopandas as gpd
        from shapely.geometry import Point
        
        geometry = [Point(x, y) for x, y in zip(sites['{}_DD'.format(lon)], sites['{}_DD'.format(lat)])]
        points = gpd.GeoDataFrame(sites, crs='epsg:4326', geometry=geometry)
        logger.info('Writing to shapefile: {}'.format(out_shp))
        points.to_file(out_shp)
