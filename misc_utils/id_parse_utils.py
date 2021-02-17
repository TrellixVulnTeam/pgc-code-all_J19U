# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""
from datetime import datetime
import logging
import re
import os
from pathlib import Path
import sys

# import tqdm
import geopandas as gpd
import pandas as pd
#import numpy as np

from selection_utils.query_danco import query_footprint
from misc_utils.dataframe_utils import determine_id_col, determine_stereopair_col
#from ids_order_sources import get_ordered_ids
from misc_utils.logging_utils import create_logger

# Set up logging
logger = create_logger(__name__, 'sh', 'INFO')

# Globals
# Path to write list of ordered IDs to
ORDERED_PATH = r'C:\code\pgc-code-all\config\ordered_ids.txt'
ORDERED_PKL = r'C:\code\pgc-code-all\config\ordered_locs.pkl'
# Directory holding order sheets
ordered_directory = r'E:\disbr007\imagery_orders'
# Offline IDs path
offline_ids_path = r'E:\pgc_index\pgcImageryIndexV6_2020nov23_offline_ids.txt'


def type_parser(filepath):
    '''
    takes a file path (or dataframe) in and determines whether it is a dbf, 
    excel, txt, csv (or df)****
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
        print('Unrecognized file type. Type: {}'.format(type(filepath)))


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
            # ids = list(df[field].unique())
            ids = list(df[field])
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
    
    # Excel
    # This assumes single column of IDs with no header row
    elif file_type == 'excel':
        df = pd.read_excel(ids_file, header=None, squeeze=True)
        if isinstance(df, pd.DataFrame):
            logger.debug('Reading only first column of excel file with multiple columns')
            df = df.iloc[:, 0]
        ids = list(df)
    # DataFrame / GeoDataFrame
    elif file_type == 'df':
        ids = list(ids_file[field])

    else:
        print('Unsupported file type... {}'.format(file_type))

    return ids


def write_ids(ids, out_path, header=None, ext='txt', append=False):
    if ext == 'txt':
        sep = '\n'
    elif ext == 'csv':
        sep = ',\n'
    if append:
        read_type = 'a'
    else:
        read_type = 'w'
    with open(out_path, read_type) as f:
        if header:
            f.write('{}{}'.format(header, sep))
        for each_id in ids:
            f.write('{}{}'.format(each_id, sep))


def write_stereopair_ids(catalogids, stereopairs, out_path, header=None, ext='csv'):
    sep = '\n'
    
    with open(out_path, 'w') as f:
        if header:
            f.write('{}{}'.format(header, sep))
        for catid, stp in zip(catalogids, stereopairs):
            f.write('{},{}{}'.format(catid, stp, sep))
            

def combine_ids(id_lists, write_path=None, fields=None):
    '''
    Takes lists of ids and combines them into a new txt file
    ids_lists: txt files of one id per line to be combined
    '''
    if not fields:
        fields = [None for id_list in id_lists]
    else:
        fields = [f if f != 'None' else None for f in fields]
    comb_ids = []

    for i, each in enumerate(id_lists):
        logger.debug('Reading IDs from: {}'.format(each))
        ids = read_ids(each, field=fields[i])
        logger.debug('IDs found: {}'.format(len(ids)))
        for i in ids:
            comb_ids.append(i)
    
    comb_ids = set(comb_ids)
    logger.debug('Total IDs found after removing any dupicates: {}'.format(len(comb_ids)))

    if write_path:
        with open(write_path, 'w') as out:
            for x in comb_ids:
                out.write('{}\n'.format(x))
    return comb_ids
    

def combine_id_files(id_files, write_path=None):
    '''
    Takes a list of filepaths to ID files and combines them into a list.

    Parameters
    ----------
    id_files : LIST
        list of paths to files containing IDs.
    write_path : os.path.abspath optional
        Path to write text file of IDs. The default is None.

    Returns
    -------
    LIST : List of IDs.

    '''
    
    all_ids = []
    for idf in id_files:
        ids = read_ids(idf)
        all_ids.extend(ids)
        
    return all_ids

    
def compare_ids(ids1_path, ids2_path, write_path=False):
    '''
    Takes two text files of ids, writes out unique to list 1, unique to list 2 and overlap
    '''
    if isinstance(ids1_path, str):
        # Get names for printing
        ids1_name = os.path.basename(ids1_path)
        ids1 = set(read_ids(ids1_path))
    else:
        ids1_name = 'ids1'
        if not isinstance(ids1_path, set):
            ids1_path = set(ids1_path)
        ids1 = ids1_path

    if isinstance(ids2_path, str):
        ids2_name = os.path.basename(ids2_path)
        ids2 = set(read_ids(ids2_path))
    else:
        ids2_name = 'ids2'
        if not isinstance(ids2_path, set):
            ids2_path = set(ids2_path)
        ids2 = ids2_path

    # Read in both ids as sets
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


def get_offline_ids():
    offline_ids = set(read_ids(offline_ids_path))
    return offline_ids


def mfp_ids(online=False):
    """
    Returns all catalogids in the current masterfootprint.
    """
    ids_path = pgc_index_path(ids=True)
    ids = set(read_ids(ids_path))
    if online is True:
        offline_ids = get_offline_ids()
        ids = ids.difference(offline_ids)

    return ids


def ordered_ids(update=False):
    """
    Returns all catalogids that are in order sheets.
    """
    if update:
        # Read all IDs in order sheets and rewrite txt file
        update_ordered()
    ordered = list(set(read_ids(ORDERED_PATH)))
    ordered = set([o for o in ordered if o != ''])

    return ordered


def onhand_ids(update=False):
    """
    Returns all ids in MFP or order sheets.
    """
    mfp = mfp_ids()
    ordered = ordered_ids(update)
    
    onhand = mfp | ordered
    
    return onhand


def remove_mfp(src):
    """
    Takes an input src of ids and removes all
    ids that are on hand.
    src: list of ids
    """
    logger.debug('Removing IDs that are in master footprint...')
    src_ids = set(src)
    # logger.debug('src_ids: {}'.format(list(src_ids)[:10]))
    onhand_ids = set(mfp_ids())
    # logger.debug('onhand ids: {}'.format(list(onhand_ids)[:10]))
    not_mfp = list(src_ids - onhand_ids)
    # logger.debug('not mfp ids: {}'.format(list(not_mfp)[:10]))
    logger.debug('IDs removed: {}'.format((len(src_ids) - len(not_mfp))))

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
    ordered = set(ordered_ids())

    not_ordered = list(src_ids - ordered)
    logger.debug('IDs removed: {}'.format((len(src_ids) - len(not_ordered))))

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


#%% Update ordered
def update_ordered(ordered_dir=None, ordered_loc=None, exclude=('NASA'),
                   new_only=True):
    # TODO: Add a config file that is a list of filepaths that have already been processed,
    # TODO: then only read files not in that list
    """Update the text file of ordered IDs by reading from order sheets"""
    from tqdm import tqdm

    # Determine location of ordered IDs
    if not ordered_loc:
        # global ordered_p
        ordered_loc = ORDERED_PATH
    if not ordered_dir:
        # global ordered_directory
        ordered_dir = ordered_directory

    # List for all IDs
    if Path(ordered_loc).exists():
        # Get last modified time for ordered list
        last_update = os.path.getmtime(ordered_loc)
        logger.info('Reading existing list of ordered ids...')
        ordered = read_ids(ordered_loc)
        logger.info('Ordered IDs found: {:,}'.format(len(ordered)))
    else:
        ordered = list()
        last_update = 0

    # Load PKL
    if Path(ORDERED_PKL).exists() and not new_only:
        df = pd.read_pickle(ORDERED_PKL)
    else:
        df = pd.DataFrame()

    ordered_locations = []

    # Progress bar set up
    total_len = sum([len(files) for r, d, files in os.walk(ordered_dir)])
    pbar = tqdm(total=total_len, desc='Iterating imagery order sheets...')

    logger.debug('Reading sheets from: {}'.format(ordered_dir))
    for root, dirs, files in os.walk(ordered_dir):
        dirs = [d for d in dirs if not any(ex in d for ex in exclude)]
        last_dir = None
        for f in files:
            f_path = os.path.join(root, f)
            if new_only:
                # Check if file newer than last update
                if not os.path.getmtime(f_path) > last_update:
                    # print('skipping already read file.')
                    continue
            cur_dir = os.path.basename(os.path.dirname(os.path.join(root, f)))
            if exclude and not any(ex in cur_dir for ex in exclude):
                if cur_dir != last_dir:
                    pbar.write('Reading from: {}'.format(cur_dir))
                ext = os.path.splitext(f)[1]
                if ext in ['.txt', '.csv', '.xls', '.xlsx']:
                    try:
                        # logger.info('Reading; {}'.format(f))
                        sheet_ids = read_ids(f_path)
                        ordered.extend(sheet_ids)
                        # Add (id, filename, date)
                        date = datetime.fromtimestamp(os.path.getmtime(f_path)).strftime('%Y-%m-%d')
                        ordered_locations.extend([(i, f, date) for i in sheet_ids])
                    except Exception as e:
                        print('failed to read: {}'.format(f))
                        logger.error(e)

                pbar.update(1)
                last_dir = cur_dir

    ordered = list(set(ordered))
    logger.info('Writing {:,} ordered IDs to: {}'.format(len(ordered), ordered_loc))
    write_ids(ordered, ordered_loc)

    new_df = pd.DataFrame.from_records(ordered_locations,
                                       columns=['catalog_id', 'loc', 'date'])

    df = pd.concat([df, new_df])
    df.sort_values(by='date', inplace=True)
    df.drop_duplicates(subset='catalog_id', keep='first')
    df.to_pickle(ORDERED_PKL)

    return df

