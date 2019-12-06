# -*- coding: utf-8 -*-
"""
Created on Wed May  1 13:16:13 2019

@author: disbr007
Module to select from Danco footprint layer based on AOI or list of IDs
"""

import geopandas as gpd
import sys, os, logging, argparse, tqdm

from id_parse_utils import read_ids
from query_danco import query_footprint
from id_parse_utils import remove_mfp

#### Logging setup
# create logger
logger = logging.getLogger('select_danco')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def determine_selection_method(selector_path, by_id):
    """
    Determines the selection type, based on the extension
    of the selector and optionally passed argument to force
    selection by ID.
    """
    if selector_path is None:
        selection_method = None
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
            
    return selection_method


def create_selector(selector_path, selection_method):
    """
    Create the selector object, based on selection_method.
    If selection method is by ID, creates a list of IDs.
    If selection method is by location, creates a geo-
    dataframe to use for selection.
    """
    if selection_method == 'ID':
        selector = read_ids(selector_path)
    elif selection_method == 'LOC':
        selector = gpd.read_file(selector_path)
    elif selection_method == None:
        selector = None
    
    return selector
    

def build_where(platforms, min_year, max_year, months, max_cc, min_cc,
                min_x1, max_x1, min_y1, max_y1):
    """
    Builds a SQL where clause based on arguments passed
    to query the footprint.
    """
    # Create string of platforms
    if platforms:
        platforms = '({})'.format(str(platforms)[1:-1])
    
    cols = {'platforms' : {'field': 'platform',   'arg_value': platforms, 'arg_comparison': 'IN'},
            'min_year'  : {'field': 'acqdate',    'arg_value': min_year,  'arg_comparison': '>='},
            'max_year'  : {'field': 'acqdate',    'arg_value': max_year,  'arg_comparison': '<='},
            'months'    : {'field': 'acqdate',    'arg_value': months,    'arg_comparison': ''},
            'max_cc'    : {'field': 'cloudcover', 'arg_value': max_cc,    'arg_comparison': '<='},
            'min_cc'    : {'field': 'cloudcover', 'arg_value': min_cc,    'arg_comparison': '>='},
            'min_x1'    : {'field': 'x1',         'arg_value': min_x1,    'arg_comparison': '>='},
            'max_x1'    : {'field': 'x1',         'arg_value': max_x1,    'arg_comparison': '<='},
            'min_y1'    : {'field': 'y1',         'arg_value': min_y1,    'arg_comparison': '>='},
            'max_y1'    : {'field': 'y1',         'arg_value': max_y1,    'arg_comparison': '<='}}

    where = ''
    for col, col_dict in cols.items():
        if col == 'months':
            if months:
                months_str = ''
                for m in months:
                    if months_str:
                        months_str += " OR "
                    m_str = "({} LIKE '%%-{}-%%')".format(col_dict['field'], m)
                    months_str += m_str
                months_str = '({})'.format(months_str)
                logging.debug('months_str {}'.format(months_str))
                if not where:
                    where += months_str
                else:
                    where += ' AND {}'.format(months_str)
        else:
            if col_dict['arg_value'] != None:
                arg_where = "({} {} {})".format(col_dict['field'], col_dict['arg_comparison'], col_dict['arg_value'])
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
    logger.info('Loading source footprint (with any provided SQL)...')
    logger.info('Loading {}...'.format(layer))
    src = query_footprint(layer=layer, where=where, columns=columns)
    logger.debug('Loaded source features before selection: {}'.format(len(src)))
    if write_source is True:
        src.to_file(r'C:\temp\src.shp')
    return src


def make_selection(selector, src, selection_method):
    '''
    Selects from a given src footprint. Decides whether to select by id (if .txt), or by location 
    (if .shp).
    sel_path: path to text file of ids, or path to shapefile
    src: geopandas dataframe of src footprint
    '''
    ## Load selection method
    logger.info("Making selection...")
    if selection_method == 'LOC':
        logger.info('Performing select by location...')
        selection = gpd.sjoin(src, selector, how='inner')
        selection.drop_duplicates(subset=['catalogid'], inplace=True) # Add field arg?
#        selection.drop(columns=list(selector), inplace=True)
    elif selection_method == 'ID':
        logger.info('Selecting by ID')
        selection = src[src['catalogid'].isin(selector)]
    
    logger.debug('Selected features: {}'.format(len(selection)))
    return selection


def remove_mfp_selection(selection):
    """
    Removes ids in the master footprint from the given selection
    """
    logger.debug('Selector type: {}'format(type(selection)))
    if type(selection) in (list, set):
        selection = remove_mfp(selection)
    # Assume dataframe
    else:
        selection = selection[selection['catalogid'].isin(remove_mfp(list(selection['catalogid'])))]
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
    logger.debug('Writing successful.')
    
    
def main(args):
    ## Parse args
    selector_path    = args.selector_path
    layer_name       = args.layer_name
    destination_path = args.destination_path
    dst_type         = args.dst_type
    by_id            = args.by_id
    columns          = args.columns
    remove_mfp       = args.remove_mfp
    
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
    
    ## Determine selection method - by location or by ID
    selection_method = determine_selection_method(selector_path, by_id)
    ## Create selector - geodataframe or list of IDs
    selector = create_selector(selector_path, selection_method)
    ## Build where clause
    where = build_where(platforms=platforms,
                        min_year=min_year,
                        max_year=max_year,
                        months=months,
                        min_cc=min_cc,
                        max_cc=max_cc,
                        min_x1=min_x1,
                        max_x1=max_x1,
                        min_y1=min_y1,
                        max_y1=max_y1)
    ## Load footprint layer with where clause
    src = load_src(layer_name, where, columns)
    ## Make selection if provided
    if selector is not None:
        selection = make_selection(selector, src, selection_method)
    else:
        selection = src
    logger.debug('Selected features before removing MFP: {}'.format(len(selection)))
    if remove_mfp is True:
        selection = remove_mfp_selection(selection)
    logger.debug('Selected features after removing MFP: {}'.format(len(selection)))
    write_selection(selection, destination_path, dst_type)


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
    
    parser.add_argument('--additional_where', type=str, default=None,
                        help='''Any additional SQL where clause to limit the 
                                chosen layer, E.g. "cloudcover < 20"''')
    
    parser.add_argument('-c', '--columns', nargs='+', default='*',
                        help='''The columns to include from the chosen layer, E.g. "catalogid acqdate".
                                Limiting the number of columns will speed up a large selection, however,
                                any columns used by selection criteria must be loaded.''')
    parser.add_argument('--remove_mfp', action='store_true',
                        help='Remove any ids that have are in the master footprint.')
    
    args = parser.parse_args()
    
    main(args)
