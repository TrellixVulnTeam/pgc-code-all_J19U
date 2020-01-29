# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""
import logging
import re
import os
import sys

import tqdm
import geopandas as gpd
import pandas as pd
#import numpy as np

from selection_utils.query_danco import query_footprint
from misc_utils.dataframe_utils import determine_id_col, determine_stereopair_col
#from ids_order_sources import get_ordered_ids
from misc_utils.logging_utils import create_logger


## Set up logging
logger = create_logger('id_parse_utils', 'sh')


def type_parser(filepath):
    '''
    takes a file path (or dataframe) in and determines whether it is a dbf, 
    excel, txt, csv (or df), ADD SUPPORT FOR SHP****
    '''
    if type(filepath) == str:
        ext = os.path.splitext(filepath)[1]
        if ext == '.csv':
            with open(filepath, 'r') as f:
                content = f.readlines()
                for row in content[0]:
                    if len(row) == 1:
                        return 'id_only_txt' # txt or csv with just ids
                    elif len(row) > 1:
                        return 'csv' # csv with columns
                    else:
                        print('Error reading number of rows in csv.')
        elif ext == '.txt':
            return 'id_only_txt' 
        elif ext in ('.xls', '.xlsx'):
            return 'excel'
        elif ext == '.dbf':
            return 'dbf'
        elif ext == '.shp':
            return 'shp'
        elif ext == '.pkl':
            return 'pkl'
    elif isinstance(filepath, gpd.GeoDataFrame):
        return 'df'
    else:
        print('Unrecognized file type.')


def get_stereopair_ids(df):
    '''
    Get's ids from stereopair column of df 
    '''
    stereopair_col = determine_stereopair_col(df)
    ids = list(df[stereopair_col])
    
    return ids


def read_ids(ids_file, field=None, sep=None, stereo=False):
    '''Reads ids from a variety of file types. Can also read in stereo ids from applicable formats
    Supported types:
        .txt: one per line, optionally with other fields after "sep"
        .dbf: shapefile's associated dbf    
    field: field name, irrelevant for text files, but will search for this name if ids_file is .dbf or .shp
    '''
    ids = []
    # Determine file type
    file_type = type_parser(ids_file)
    # Text file
    if file_type == 'id_only_txt':
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
    # DBF
    elif file_type == 'dbf':
        df = gpd.read_file(ids_file)
        if field == None:
            id_col = determine_id_col(df)
        else:
            id_col = field
        df_ids = list(df[id_col])
        for each_id in df_ids:
            ids.append(each_id)
        # If stereopairs are desired, find them
        if stereo == True:
            sp_ids = get_stereopair_ids(df)
            for sp_id in sp_ids:
                ids.append(sp_id)
    # SHP
    elif file_type == 'shp':
        df = gpd.read_file(ids_file)
        if field:
            ids = list(df[field].unique())
        else:
            id_fields = ['catalogid', 'catalog_id', 'CATALOGID', 'CATALOG_ID']
            field = [x for x in id_fields if x in list(df)]
            if len(field) != 1:
                logger.error('Unable to read IDs, no known ID fields found.')
            else:
                field = field[0]
            ids = df[field].unique()

    # PKL
    elif file_type == 'pkl':
        logger.warning('Loading IDs from pkl, not sure if this works...')
        df = pd.read_pickle(ids_file)
        if len(df.columns) > 1:
            ids = list(df[df.columns[0]])
        elif len(df.columns) == 1:
            ids = list(df)
        else:
            print('No columns found in pickled dataframe.')
    else:
        print('Unsupported file type... {}'.format(file_type))

    return ids


def write_ids(ids, out_path, header=None, ext='txt'):
    if ext == 'txt':
        sep = '\n'
    elif ext == 'csv':
        sep = ',\n'
    
    with open(out_path, 'w') as f:
        if header:
            f.write('{}{}'.format(header, sep))
        for each_id in ids:
            f.write('{}{}'.format(each_id, sep))
            

def combine_ids(*id_lists, write_path=None):
    '''
    Takes lists of ids and combines them into a new txt file
    ids_lists: txt files of one id per line to be combined
    '''
    comb_ids = []
    for each in id_lists:
        ids = read_ids(each)
        for i in ids:
            comb_ids.append(i)
    if write_path:
        with open(write_path, 'w') as out:
            for x in comb_ids:
                out.write('{}\n'.format(x))
    return comb_ids
    
    
def compare_ids(ids1_path, ids2_path, write_path=False):
    '''
    Takes two text files of ids, writes out unique to list 1, unique to list 2 and overlap
    '''
    if isinstance(ids1_path, str):
        # Get names for printing
        ids1_name = os.path.basename(ids1_path)
    else:
        ids1_name = 'ids1'

    if isinstance(ids2_path, str):
        ids2_name = os.path.basename(ids2_path)
    else:
        ids2_name = 'ids2'

    # Read in both ids as sets
    ids1 = set(read_ids(ids1_path))
    ids2 = set(read_ids(ids2_path))
    for id_list in [(ids1_name, ids1), (ids2_name, ids2)]:
        print('IDs in {}: {:,}'.format(id_list[0], len(id_list[1])))
    
    ## Get ids unique to each list and those common to both
    # Unique
    print('\nFinding unique...')
    ids1_u = ids1 - ids2
    ids2_u = ids2 - ids1
    for id_list in [(ids1_name, ids1_u), (ids2_name, ids2_u)]:
        print('Unique in {}: {:,}'.format(id_list[0], len(id_list[1])))
    
    # Common
    print('\nFinding common...')
    ids_c = [x for x in ids1 if x in ids2]
    print('\nCommon: {:,}'.format(len(ids_c)))
    
    if write_path:
        for id_list in [(ids1_path, ids1_u), (ids2_path, ids2_u)]:
            out_dir = os.path.dirname(id_list[0])
            name = os.path.basename(id_list[0]).split('.')[0]
            if len(id_list[1]) != 0:
                write_ids(id_list[1], os.path.join(out_dir, '{}_unique.txt'.format(name)))
        if len(ids_c) != 0:
            write_ids(ids_c, os.path.join(out_dir, 'common.txt'))
    
    return ids1_u, ids2_u, ids_c


def date_words(date=None, today=False):
    '''get todays date and convert to '2019jan07' style for filenaming'''
    from datetime import datetime, timedelta
    if today == True:
        date = datetime.now() - timedelta(days=1)
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    year = date.strftime('%Y')
    month = date.strftime('%b').lower()
    day = date.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date


def archive_id_lut():
    from query_danco import query_footprint
    
    # Look up table names on danco
    print('Creating look-up table from danco table...')
    
    luts = {
            'GE01': 'index_dg_catalogid_to_ge_archiveid_ge01',
            'IK01': 'index_dg_catalogid_to_ge_archiveid_ik'
            }
    
    # Verify sensor
#    if sensor in luts:
#        pass
#    else:
#        print('{} look up table not found. Sensor must be in {}'.format(sensor, luts.keys()))
    
    # Create list to store tuples of (old id, new id)
    lut = []
    
    # Create tuples for each sensor, append to list
    for sensor in luts.keys():
        lu_df = query_footprint(layer=luts[sensor], table=True)
        # Combine old ids and new ids in tuples in a list
        sensor_lut = list(zip(lu_df.crssimageid, lu_df.catalog_identifier))
        for entry in sensor_lut:
            lut.append(entry)
    
    # Convert list of tuples to dictionary
    lu_dict = dict(lut)
    
    return lu_dict
    

def ge_ids2dg_ids(ids):
    '''
    takes a list of old GE ids and converts them to DG
    '''
    ## Assess what is in the list of ids
    print('Total ids in list: {}'.format(len(ids)))
    num_dg_style = len([x for x in ids if len(x) == 16])
    num_ge_style = len([x for x in ids if len(x) != 16])
    
    print('DG style ids: {}'.format(num_dg_style)) # DG style if 16 char (true?)
    print('Old style ids: {}'.format(num_ge_style))
    
    # Set up lists to store ids
    converted_ids = [] # ids to write out (DG style)
    convertable_ids = [] # ids that were converted (old style)
    not_conv_ids = [] # Ids that were not converted
    
    join_table = pd.DataFrame(columns=['catalogid', 'out_ids'])
    
    # Get list of all old ids for counting how many ids get converted
#    sensors = ['IK01', 'GE01']
#    for sensor in sensors:
#    print('Converting {} ids...'.format())
    # Look up table only for given sensor
    lu_dict = archive_id_lut()
    
    # Read ids into dataframe
    id_df = pd.DataFrame(ids, columns=['catalogid'])
    
    # Convert old ids that are in the look-up to DG style
    id_df['out_ids'] = id_df['catalogid'].map(lu_dict)
    
    # Copy ids that are already DG style to new column (where len catid is 16, make 'out_ids' = catid)     
    id_df.loc[id_df.catalogid.str.len() == 16, 'out_ids'] = id_df.catalogid

    
    join_table = pd.concat([join_table, id_df])
    
    # Add all converted, new style IDs to list
    for the_id in list(id_df.out_ids[~id_df.out_ids.isnull()]):
        converted_ids.append(the_id)

    # Create list of old style that were changed -> for removing from not converable (due to loop)
    for the_id in list(id_df.catalogid[~id_df.out_ids.isnull()]):
        convertable_ids.append(the_id)
            
    # List all not converted ids
    for the_id in list(id_df.catalogid[id_df.out_ids.isnull()]):
        not_conv_ids.append(the_id)

    converted_ids = list(set(converted_ids))
    not_conv_ids = list(set(not_conv_ids) - set(convertable_ids))
    
    print('Converted or already DG style ids: {}'.format(len(converted_ids)))
    print('Not convertable ids: {}'.format(len(not_conv_ids)))

    return converted_ids, not_conv_ids


def pgc_index_path(ids=False):
    '''
    Returns the path to the most recent pgc index from a manually updated
    text file containing the path.
    '''
    with open(r'C:\code\pgc-code-all\config\pgc_index_path.txt', 'r') as src:
        content = src.readlines()
    if not ids:
        index_path = content[0].strip('\n')
    if ids:
        index_path = content[1].strip('\n')
    logger.debug('PGC index path loaded: {}'.format(index_path))
    return index_path


def locate_ids(df, cat_id_field):
    '''
    Creates a new column in df with the location of each catalogid - prioritizing PGC, then NASA, then ordered.
    df: dataframe containing catalogids
    cat_id_field: field name with catalogids
    '''
    logger.error("""locate_ids function in id_parse_utils not functional, 
                    circular dependency with get_ordered_ids function in 
                    ids_order_source.py""")
    # def locate_id(each_id, pgc_ids, nasa_ids, ordered_ids):
    #     '''
    #     Returns where a single id is located.
    #     '''
    #     if each_id in pgc_ids:
    #         location = 'pgc'
    #     elif each_id in nasa_ids:
    #         location = 'nasa'
    #     elif each_id in ordered_ids:
    #         location = 'ordered'
    #     else:
    #         location = 'unknown'
    #     return location

    # pgc_ids = set(read_ids(r'C:\pgc_index\catalog_ids.txt')) # mfp
    # nasa_ids = set(read_ids(r'C:\pgc_index\nga_inventory_canon20190505\nga_inventory_canon20190505_CATALOG_ID.txt')) # nasa
    # ordered_ids = set(get_ordered_ids()) #order sheets
    
    # df['location'] = df[cat_id_field].apply(lambda x: locate_id(x, pgc_ids, nasa_ids, ordered_ids))


def mfp_ids():
    """
    Returns all catalogids in the current masterfootprint.
    """
    ids_path = pgc_index_path(ids=True)
    ids = read_ids(ids_path)
    return ids


def remove_mfp(src):
    """
    Takes an input src of ids and removes all 
    ids that are on hand.
    src: list of ids
    """
    logger.debug('Removing IDs in master footprint...')
    logger.debug('Removing mfp ids...')
    src_ids = set(src)
    logger.debug('src_ids: {}'.format(list(src_ids)[:10]))
    onhand_ids = set(mfp_ids())
    logger.debug('onhand ids: {}'.format(list(onhand_ids)[:10]))
    not_mfp = list(src_ids - onhand_ids)
    logger.debug('not mfp ids: {}'.format(list(not_mfp)[:10]))
    logger.debug('IDs removed: {}'.format((len(src_ids)-len(not_mfp))))
    
    return not_mfp


def remove_ordered(src):
    """
    Takes an input src of ids and removes all
    ids that have been ordered.
    src: list of ids
    """
    logger.debug('Removing IDs in order sheets...')
    logger.debug('Removing ordered...')
    src_ids = set(src)
    ordered_p = r'E:\disbr007\imagery_orders\ordered\all_ordered.txt'
    ordered = set(read_ids(ordered_p))
    
    not_ordered = list(src_ids - ordered)
    logger.debug('IDs removed: {}'.format((len(src_ids)-len(not_ordered))))
    
    return not_ordered


def remove_onhand(src):
    """
    Takes an input src of ids and removes all
    ids that are either in the mfp or ordered.
    src: list of ids
    """
    not_mfp = remove_mfp(src)
    not_mfp_ordered = remove_ordered(not_mfp)
    
    return not_mfp_ordered


def parse_filename(filename, att, fullpath=False):
    """
    Parses a PGC renamed file name and returns the requested 
    attribute.
    filename : STR
        A PGC renamed raster filename
    att : STR
        Attribute to return, one of: 
            'catalog_id', 'scene_id', 'prod_code', 'platform'
            'acq_time', 'date', 'date_words'
    fullpath : BOOLEAN
        Whether filename is a fullpath or just a basename
    """
    if fullpath == True:
        filename = os.path.basename(filename)
    try:
        # Parse filename
        scene_id = filename.split('.')[0]
        # Remove filename suffixes, breaking at '_' until 'P0 is found
        sid_found = False
        while sid_found == False:
            if scene_id.split('_')[-1].startswith('P0'):
                scene_id = '_'.join(scene_id.split('_'))
                sid_found = True
            else:
                if len(scene_id.split('_')) == 2:
                    logger.error("""Error parsing filename: {}
                                    Could not find {}""".format(filename, att))
                    sys.exit()
                scene_id = '_'.join(scene_id.split('_')[:-1])
                
        # if scene_id.split('_')[-1].startswith('u'):
            # logger.debug("Ortho'd filename provided.")
            # scene_id = '_'.join(scene_id.split('_')[:-1])
        first, prod_code, _third = scene_id.split('-')
        platform, _date, catalogid, _date_words = first.split('_')
        date = '{}-{}-{}'.format(_date[:4], _date[4:6], _date[6:8])
        acq_time = '{}T{}:{}:{}'.format(date, _date[8:10], _date[10:12], _date[12:14])
        date_words = _date_words[:8]
    
        att_lut = {'scene_id': scene_id,
                   'prod_code': prod_code,
                   'platform': platform,
                   'catalog_id': catalogid,
                   'date': date,
                   'acq_time': acq_time,
                   'date_words': date_words}
        try:
            requested_att = att_lut[att]
        except KeyError as e:
            logger.warning('Requested attribute "{}" not found.'.format(att))
            logger.error(e)
            requested_att = None
    except Exception as e:
        logger.warning('Error with file {}'.format(filename))
        logger.error(e)
        raise e
        requested_att = None
    
    return requested_att


def get_platform(catalogid):
    platform_code = {
                '101': 'QB02',
                '102': 'WV01',
                '103': 'WV02',
                '104': 'WV03',
                '104A': 'WV03-SWIR',
                '105': 'GE01',
                '106': 'IK01'
                }
    for key, val in platform_code.items():
        if catalogid.startswith(key):
            platform = val
        else:
            platform = 'NA'


def get_platform_code(platform):
    platform_code = {
                'QB02': '101',
                'WV01': '102',
                'WV02': '103',
                'WV03': '104',
                'WV03-SWIR': '104A',
                'GE01': '105',
                'IK01': '106'
                }

    return platform_code[platform]


def is_stereo(dataframe, catalogid_field, out_field='is_stereo'):
    """
    Takes a dataframe and determines if each catalogd in catalogid_field
    is a stereo image.
    """
    stereo_ids = query_footprint('pgc_imagery_catalogids_stereo', 
                                 table=True, 
                                 columns=['CATALOG_ID'])
    stereo_ids = list(stereo_ids)
    dataframe[out_field] = dataframe[catalogid_field].apply(lambda x: x in stereo_ids)
    

def dem_exists(dataframe, catalogid_field, out_field='dem_exists'):
    """
    Takes a dataframe and determines if each catalogid in catalogid_field
    has been turned into a DEM.

    Parameters
    ----------
    dataframe : pd.DataFrame or gpd.GeoDataFrame
        Dataframe of one ID per row.
    catalogid_field : STR
        Field in dataframe with catalogids.
    out_field : TYPE, optional
        The name of the field to create. The default is 'dem_exists'.

    Returns
    -------
    None.

    """
    dems = query_footprint('pgc_dem_setsm_strips', table=True, columns=['catalogid1', 'catalogid2'])
    dem_ids = list(dems['catalogid1']) + list(dems['catalogid2'])
    dataframe[out_field] = dataframe[catalogid_field].apply(lambda x: x in dem_ids)


def create_s_filepath(scene_id, strip_id, acqdate, prod_code):
    base = r'V:/pgc/data/sat/orig'
    sensor = scene_id[:4]
    pd = prod_code[1:3]
    year = acqdate[:4]
    month_num = acqdate[5:7]
    month_names = {'01':'jan',
                   '02':'feb',
                   '03':'mar',
                   '04':'apr',
                   '05':'may',
                   '06':'jun',
                   '07':'jul',
                   '08':'aug',
                   '09':'sep',
                   '10':'oct',
                   '11':'nov',
                   '12':'dec'}
    month = '{}_{}'.format(month_num, month_names[month_num])

    s_filepath = '/'.join([base, sensor, pd, year, month, strip_id, '{}.ntf'.format(scene_id)])
    
    return s_filepath
