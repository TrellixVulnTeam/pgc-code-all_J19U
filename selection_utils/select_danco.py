# -*- coding: utf-8 -*-
"""
Created on Wed May  1 13:16:13 2019

@author: disbr007
Module to select from Danco footprint layer based on AOI or list of IDs
"""

import geopandas as gpd
import sys, os, logging, argparse, tqdm

from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import read_ids, remove_mfp, mfp_ids
from selection_utils.query_danco import query_footprint, layer_fields


# Logging
logger = create_logger(__name__, 'sh', handler_level='DEBUG')


def determine_selection_method(selector_path, by_id):
    """
    Determines the selection type, based on the extension
    of the selector and optionally passed argument to force
    selection by ID.
    """
    if selector_path is None:
        selection_method = None
    else:
        if by_id is True:
            selection_method = 'ID'
        else:
            ext = os.path.basename(selector_path).split('.')[1]
            
            # If text, select by id
            if ext == 'txt':
                selection_method = 'ID'
            # If .shp, select by location
            elif ext == 'shp':
                selection_method = 'LOC'
            else:
                selection_method = None
                logger.error('Unknown file format for selection. Supported formats: .txt and .shp')
    logger.info('Selection method: {}'.format(selection_method))

    return selection_method


def create_selector(selector_path, selection_method):
    """
    Create the selector object, based on selection_method.
    If selection method is by ID, creates a list of IDs.
    If selection method is by location, creates a geo-
    dataframe to use for selection.
    """
    logger.debug('Creating selector from: {}'.format(os.path.basename(selector_path)))
    if selection_method == 'ID':
        selector = read_ids(selector_path)
    elif selection_method == 'LOC':
        selector = gpd.read_file(selector_path)
    elif not selection_method:
        selector = None

    return selector


def check_alt_field_names(field_name, table_name, table_fields=None):
    """
    Checks to see if the field name is in the given table. If not, checks
    to see if other, comparable field names are. If so, it returns them,
    if not it returns None.

    Parameters
    ----------
    field_name : str
        The field name to check.
    table_name: str
        The danco table to try to match to.

    Returns
    -------
    Corrected field name if found, otherwise None.
    """
    logger.debug('Looking for field "{}" in table "{}"'.format(field_name, table_name))
    if not table_fields:
        table_fields = layer_fields(table_name)

    checked_field_name = None
    if field_name in table_fields:
        logger.debug('Field "{}" found in {}'.format(field_name, table_name))
        checked_field_name = field_name
    else:
        alt_dict = {'platform':    ['platform', 'sensor', 'sensor1', 'sensor2', 'SENSOR'],
                    'acqdate':     ['acqdate', 'ACQDATE', 'acqdate1', 'acqdate2'],
                    'cloudcover':  ['cloudcover', 'cloudcover1', 'cloudcover2'],
                    'x1':          ['x1', 'cent_lon'],
                    'y1':          ['y1', 'cent_lat'],
                    'catalogid':   ['catalogid', 'CATALOGID', 'catalogid1', 'catalogid2'],
                    }
        for key, alt_fields in alt_dict.items():
            if field_name in alt_fields:
                logger.debug('Found field "{}" in alternate field dictionary.'.format(field_name))
                for alt_field in alt_fields:
                    if alt_field in table_fields:
                        logger.debug('Matched {} to alt name: {}.'.format(field_name, alt_field))
                        checked_field_name = alt_field
                        break
                    else:
                        logger.debug('Tried "{}", not in {}'.format(alt_field, table_name))
                break
            else:
                checked_field_name = None
                logger.error('Cannot locate field {} in table {}'.format(field_name, table_name))
    if checked_field_name == None:
        logger.debug('Cannot locate field "{}" in "{}"'.format(field_name, table_name))
    
    return checked_field_name


def build_where(platforms=None, min_year=None, max_year=None, months=None,
                max_cc=None, min_cc=None, min_x1=None, max_x1=None, 
                min_y1=None, max_y1=None, layer_name=None):
    """
    Builds a SQL where clause based on arguments passed
    to query the footprint.
    """
    # Create string of platforms
    if platforms is not None:
        platforms = '({})'.format(str(platforms)[1:-1])

    cols = {'platforms' : {'field': 'platform',   'arg_value': platforms, 'arg_comparison': 'IN', 'field_type': str},
            'min_year'  : {'field': 'acqdate',    'arg_value': min_year,  'arg_comparison': '>=', 'field_type': str}, 
            'max_year'  : {'field': 'acqdate',    'arg_value': max_year,  'arg_comparison': '<=', 'field_type': str},
            'months'    : {'field': 'acqdate',    'arg_value': months,    'arg_comparison': ''},
            'max_cc'    : {'field': 'cloudcover', 'arg_value': max_cc,    'arg_comparison': '<=', 'field_type': int},
            'min_cc'    : {'field': 'cloudcover', 'arg_value': min_cc,    'arg_comparison': '>=', 'field_type': int},
            'min_x1'    : {'field': 'x1',         'arg_value': min_x1,    'arg_comparison': '>=', 'field_type': float},
            'max_x1'    : {'field': 'x1',         'arg_value': max_x1,    'arg_comparison': '<=', 'field_type': float},
            'min_y1'    : {'field': 'y1',         'arg_value': min_y1,    'arg_comparison': '>=', 'field_type': float},
            'max_y1'    : {'field': 'y1',         'arg_value': max_y1,    'arg_comparison': '<=', 'field_type': float}}

    where = ''
    table_fields = layer_fields(layer_name)
    for col, col_dict in cols.items():
        # Check if arg provided
        if col_dict['arg_value']:
            # Check if current col in layer fields, if not try alternate names
            if layer_name is not None:
                field = check_alt_field_names(col_dict['field'], layer_name, table_fields=table_fields)
            else:
                field = col_dict['field']

            if col == 'months':
                if months:
                    months_str = ''
                    for m in months:
                        if months_str:
                            months_str += " OR "
                        m_str = "({} LIKE '%%-{}-%%')".format(field, m)
                        months_str += m_str
                    months_str = '({})'.format(months_str)
                    logging.debug('months_str {}'.format(months_str))
                    if not where:
                        where += months_str
                    else:
                        where += ' AND {}'.format(months_str)
            else:
                if col_dict['arg_value'] != None:
                    if col_dict['field_type'] == str:
                        arg_where = "({} {} '{}')".format(field, col_dict['arg_comparison'], col_dict['arg_value'])
                    else:
                        arg_where = "({} {} {})".format(field, col_dict['arg_comparison'], col_dict['arg_value'])
                    if not where:
                        where += arg_where
                    else:
                        where += ' AND {}'.format(arg_where)
    logger.debug('Using where clause: {}'.format(where))

    return where


def load_src(layer, where, columns, write_source=False):
    """
    Load danco layer specified with where clause and columns provided.
    """
    ## Load source footprint
    logger.debug('Loading source footprint (with any provided SQL)...')
    logger.debug('Loading {}...'.format(layer))
    src = query_footprint(layer=layer, where=where, columns=columns)
    logger.info('Loaded source features before selection: {}'.format(len(src)))
    if write_source is True:
        src.to_file(r'C:\temp\src.shp')
    return src


def make_selection(selector, src, selection_method, drop_dup=None):
    '''
    Selects from a given src footprint. Decides whether to select by id (if .txt), or by location 
    (if .shp).
    sel_path: path to text file of ids, or path to shapefile
    src: geopandas dataframe of src footprint
    '''
    # Load selection method
    logger.debug("Making selection...")
    if selection_method == 'LOC':
        logger.debug('Performing select by location...')
        if selector.crs != src.crs:
            logger.debug('Selector CRS != source CRS. Reprojecting selector CRS to match.')
            selector = selector.to_crs(src.crs)
        selection = gpd.sjoin(src, selector, how='inner')
        if drop_dup is not None:
            logger.debug('Dropping duplicate "{}" records'.format(drop_dup))
            selection.drop_duplicates(subset=drop_dup, inplace=True) # Add field arg?
#        selection.drop(columns=list(selector), inplace=True)
    elif selection_method == 'ID':
        logger.debug('Selecting by ID')
        catid_fields = [f for f in list(src) if 'catalogid' in f]
        selection = src[src[catid_fields[0]].isin(selector)]

    logger.info('Selected features: {}'.format(len(selection)))

    return selection


def remove_mfp_selection(selection):
    """
    Removes ids in the master footprint from the given selection
    """
    logger.debug('Selector type: {}'.format(type(selection)))
    if type(selection) in (list, set):
        selection = remove_mfp(selection)
    # Assume dataframe
    else:
        catid_fields = [f for f in list(selection) if 'catalogid' in f]
        selection = selection[selection[catid_fields[0]].isin(remove_mfp(list(selection[catid_fields[0]])))]

    return selection


def keep_mfp_selection(selection, stereo=True):
    """Keep only IDs in master footprint from given selection"""
    logger.debug('Keeping only IDs in the master footprint.')
    logger.debug('IDs before keeping only MFP: {}'.format(len(selection)))
    oh_ids = set(mfp_ids())
    if type(selection) in (list, set):
        selection = set(selection).intersection(oh_ids)
    else:
        catid_field = [f for f in list(selection) if 'catalogid' in f][0]
        selection = selection[selection[catid_field].isin(oh_ids)]
        if stereo:
            logger.debug('Keeping where stereopair also in MFP.')
            stp_field = [f for f in list(selection) if 'stereopair' in f][0]
            selection = selection[selection[stp_field].isin(oh_ids)]


    logger.debug('IDs after keeping only MFP: {}'.format(len(selection)))
    return selection


def write_selection(selection, destination_path, dst_type):
    """
    Write the selection to destination path, either as shp or txt of IDs
    """
    logger.info('Writing to {}...'.format(destination_path))
    if dst_type is None:
        ext = os.path.basename(destination_path).split('.')[1]
        dst_type = ext
    if dst_type == 'shp':
        selection.to_file(destination_path)
    elif dst_type == 'txt':
        with open(destination_path, 'w') as dst:
            for each_id in selection:
                dst.write('{}\n'.format(each_id))
    logger.info('Writing successful.')


def select_danco(layer_name, destination_path=None, selector_path=None, dst_type=None,
                 by_id=None, remove_mfp=None, keep_mfp_ids=False, keep_mfp_stereo=True,
                 platforms=None, min_year=None, max_year=None, months=None,
                 min_cc=None, max_cc=None,
                 min_x1=None, max_x1=None, min_y1=None, max_y1=None,
                 columns='*', drop_dup=None, add_where=None,
                 use_land=None):
    if selector_path:
        # Determine selection method - by location or by ID
        selection_method = determine_selection_method(selector_path, by_id)
        # Create selector - geodataframe or list of IDs, or None
        logger.debug('Creating selector...')
        selector = create_selector(selector_path, selection_method)
        # Build where clause
    else:
        selector = None
    logger.debug('Building where clause')
    where = build_where(platforms=platforms,
                        min_year=min_year,
                        max_year=max_year,
                        months=months,
                        min_cc=min_cc,
                        max_cc=max_cc,
                        min_x1=min_x1,
                        max_x1=max_x1,
                        min_y1=min_y1,
                        max_y1=max_y1,
                        layer_name=layer_name)
    if add_where:
        if where:
            where += " AND "
        where += """ {}""".format(add_where)
    logger.debug('Where clause: {}'.format(where))
    # Load footprint layer with where clause
    src = load_src(layer_name, where, columns)
    logger.info('Loaded source layer with SQL clause: {:,}'.format(len(src)))
    if len(src) == 0:
        logger.warning('No features selected. Exiting.')
        sys.exit()
    # Make selection if provided
    if selector is not None:
        selection = make_selection(selector, src, selection_method, drop_dup=drop_dup)
    else:
        selection = src

    if use_land:
        logger.info('Selecting only records within land inclusion shapefile...')
        land_shp = r'E:\disbr007\imagery_orders\coastline_include_fix_geom_dis.shp'
        land = gpd.read_file(land_shp)
        # Drop 'index' columns if they exists
        # drop_cols = [x for x in list(noh_recent_roi) if 'index' in x]

        # noh_recent_roi = noh_recent_roi.drop(columns=drop_cols)
        selection = gpd.sjoin(selection, land, how='left')


    if remove_mfp:
        logger.info('Selected features before removing MFP: {:,}'.format(len(selection)))
        selection = remove_mfp_selection(selection)
        logger.info('Selected features after removing MFP: {}'.format(len(selection)))
    if keep_mfp_ids:
        selection = keep_mfp_selection(selection, stereo=keep_mfp_stereo)

    if destination_path is not None:
        write_selection(selection, destination_path, dst_type)

    return selection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layer_name', type=str,
                        help='The danco footprint layer name to select from. E.g "index_dg"')
    parser.add_argument('destination_path', type=os.path.abspath,
                        help='''Location to write selection to.''')
    parser.add_argument('--dst_type', type=str,
                        help='''Type of file to write, either "shp" or "txt".
                                If not provided, infered from extension of
                                destination_path.''')
    parser.add_argument('--selector_path', type=os.path.abspath,
                        help='''The path to the selector to use. If not provided,
                                only the SQL arguments are applied to the danco layer.
                                Supported extensions:
                                .txt: results in a select by ID
                                .shp: defaults to select by location, use --by_id
                                to force select by ID with shp.''')

    parser.add_argument('--by_id', action='store_true',
                        help='Force select by ID when a shape is provided.')

    parser.add_argument('--platforms', nargs='+',
                        help='Sensors to include.')
    parser.add_argument('--min_year', type=str, help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, help='Latest year to include')
    parser.add_argument('--months', nargs='+', help='Months to include. E.g. 01 02 03')

    parser.add_argument('--min_cc', type=int, help='Minimum cloudcover to include.')
    parser.add_argument('--max_cc', type=int, help='Max cloudcover to include.')

    parser.add_argument('--min_long', type=int, help='Minimum x (longitude) of footprints - in DD.')
    parser.add_argument('--max_long', type=int, help='Maximum x (longitude) of footprints - in DD.')
    parser.add_argument('--min_lat', type=int, help='Minimum y (latitude) of footprints - in DD.')
    parser.add_argument('--max_lat', type=int, help='Maximum y (latitude) of footprints - in DD.')

    parser.add_argument('--add_where', type=str,
                        help='''Any additional SQL where clause to limit the
                                chosen layer, E.g. "cloudcover < 20"''')
    parser.add_argument('-c', '--columns', nargs='+',
                        help='''The columns to include from the chosen layer, E.g. "catalogid acqdate".
                                Limiting the number of columns will speed up a large selection, however,
                                any columns used by selection criteria must be loaded.''')
    parser.add_argument("--use_land", action='store_true',
                        help="Use coastline inclusion shapefile.")
    parser.add_argument('--remove_mfp_ids', action='store_true',
                        help='Remove any ids that are in the master footprint.')
    parser.add_argument('--keep_mfp_ids', action='store_true',
                        help='Keep only IDs that are in the master footprint.')


    args = parser.parse_args()

    # Parse args
    selector_path    = args.selector_path
    layer_name       = args.layer_name
    destination_path = args.destination_path
    dst_type         = args.dst_type
    by_id            = args.by_id
    columns          = args.columns
    remove_mfp_ids   = args.remove_mfp_ids
    keep_mfp_ids     = args.keep_mfp_ids
    use_land         = args.use_land

    platforms = args.platforms
    min_year  = args.min_year
    max_year  = args.max_year
    months    = args.months
    min_cc    = args.min_cc
    max_cc    = args.max_cc
    min_x1    = args.min_long
    max_x1    = args.max_long
    min_y1    = args.min_lat
    max_y1    = args.max_lat
    add_where = args.add_where

    select_danco(selector_path=selector_path,
                 layer_name=layer_name,
                 destination_path=destination_path,
                 dst_type=dst_type,
                 by_id=by_id,
                 columns=columns,
                 remove_mfp=remove_mfp_ids,
                 keep_mfp_ids=keep_mfp_ids,
                 platforms=platforms,
                 min_year=min_year,
                 max_year=max_year,
                 months=months,
                 min_cc=min_cc,
                 max_cc=max_cc,
                 min_x1=min_x1,
                 max_x1=max_x1,
                 min_y1=min_y1,
                 max_y1=max_y1,
                 add_where=add_where,
                 use_land=use_land)
