# -*- coding: utf-8 -*-
"""
Created on Wed May  1 13:16:13 2019

@author: disbr007
Module to select from Danco footprint layer based on AOI or list of IDs
"""

import geopandas as gpd
import sys, os, logging, argparse, tqdm

from query_danco import query_footprint
from id_parse_utils import read_ids

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
    
    return selector
    

def build_where(platforms, min_year, max_year, months, max_cc, min_cc,
                min_x1, max_x1, min_y1, max_y1):
    """
    Builds a SQL where clause based on arguments passed
    to query the footprint.
    """
    cols = {'platforms' : {'field': 'platform', 'arg_value': platforms, 'arg_comparison': 'IN'},
            'min_year'  : {'field': 'acqdate',  'arg_value': min_year,  'arg_comparison': '>='},
            'max_year'  : {'field': 'acqdate',  'arg_value': max_year,  'arg_comparison': '<='},
#            'months'    : {'field': , 'arg_value': , 'arg_comparison':},
            'max_cc'    : {'field': 'cloudcover', 'arg_value': max_cc, 'arg_comparison': '<='},
            'min_cc'    : {'field': 'cloudcover', 'arg_value': min_cc, 'arg_comparison': '>='},
            'min_x1'    : {'field': 'x1',         'arg_value': min_x1, 'arg_comparison': '>='},
            'max_x1'    : {'field': 'x1',         'arg_value': max_x1, 'arg_comparison': '<='},
            'min_y1'    : {'field': , 'arg_value': , 'arg_comparison':},
            'max_y1'    : {'field': , 'arg_value': , 'arg_comparison':}}
    where = ""
    

def load_src(layer, where=None, columns=None):
    ## Load source footprint
    logger.info('Loading source footprint (with any provided SQL)...')
    layer = layer
    logger.info('Loading {}...'.format(layer))
    src = query_footprint(layer=layer, where=where, columns=columns)
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
        selection = gpd.sjoin(selector, src, how='inner')
        selection.drop_duplicates(subset=['catalogid'], inplace=True) # Add field arg?
        selection.drop(columns=list(selector), inplace=True)
        
    return selection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('selector_path', type=str, 
                        help='''The path to the selector to use. Supported extensions: 
                            .txt: results in a select by ID
                            .shp: defaults to select by location, use --by_id to force select by ID.''')
    parser.add_argument('layer_name', type=str,
                        help='The danco footprint layer name to select from. E.g "index_dg"')
    parser.add_argument('destination_path', type=str,
                        help='''Location to write selection to.''')

    parser.add_argument('--dst_type', type=str, default='shp',
                        help='''Type of the file to write, either "shp" or "txt".''')
    
    parser.add_argument('--by_id', action='store_true',
                        help='Force select by ID when a shape is provided.')
    
    parser.add_argument('--platforms', nargs='+',
                        help='Sensors to include.')
    parser.add_argument('--min_year', type=str, help='Earliest year to include.')
    parser.add_argument('--max_year', type=str, help='Latest year to include')
    parser.add_argument('--months', nargs='+', help='Months to include. E.g. 01 02 03')
    
    parser.add_argument('--min_cc', type=int, help='Minimum cloudcover to include.')
    parser.add_argument('--max_cc', type=int, help='Max cloudcover to include.')
    
    parser.add_argument('--min_x1', type=int, help='Minimum x (longitude) of footprints - in DD.')
    parser.add_argument('--max_x1', type=int, help='Maximum x (longitude) of footprints - in DD.')
    parser.add_argument('--min_y1', type=int, help='Minimum y (latitude) of footprints - in DD.')
    parser.add_argument('--max_y1', type=int, help='Maximum y (latitude) of footprints - in DD.')
    
    parser.add_argument('-w', '--where', type=str, default=None,
                        help='''Any additional SQL where clause to limit the 
                                chosen layer, E.g. "cloudcover < 20"''')
    
    parser.add_argument('-c', '--columns', nargs='+', default='*',
                        help='''The columns to include from the chosen layer, E.g. "catalogid acqdate".
                                Limiting the number of columns will speed up a large selection, however,
                                any columns used by selection criteria must be loaded.''')
    
    
    args = parser.parse_args()
    
    