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

## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(filename=r'E:\disbr007\scratch\fp_density.log', 
                    filemode='w', 
                    format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.DEBUG)

lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


def load_src(layer, where=None, columns=None):
    ## Load source footprint
    layer = layer
    where = where=where
    columns = columns
    logging.info('Loading {}...'.format(layer))
    src = query_footprint(layer=layer, where=where, columns=columns)
    return src


def make_selection(sel_path, src):
    '''
    Selects from a given src footprint. Decides whether to select by id (if .txt), or by location 
    (if .shp).
    sel_path: path to text file of ids, or path to shapefile
    src: geopandas dataframe of src footprint
    '''
    ## Load selection method
    ext = os.path.basename(sel_path).split('.')[1]
    
    # If text, select by id
    if ext == 'txt':
        ids = read_ids(sel_path)
        selection = src[src.catalogid.isin(ids)]
    
    # If .shp, select by location
    elif ext == 'shp':
        logging.info('Performing spatial join...')
        driver = 'ESRI Shapefile'
        sel = gpd.read_file(sel_path, driver=driver)
        selection = gpd.sjoin(src, sel, how='inner')
    
    else:
        selection = None
        print('Unknown file format for selection. Supported formats: .txt and .shp')
        
    return selection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('selector_path', type=str, 
                        help='The path to the selector to use. Supported extensions: .txt, .shp.')
    parser.add_argument('layer_name', type=str,
                        help='The danco footprint layer name to select from. E.g "index_dg"')
    parser.add_argument('-w', '--where', type=str, default=None,
                        help='The SQL clause to limit the chosen layer, E.g. "cloudcover < 20"')
    parser.add_argument('-c', '--columns', nargs='+', default='*',
                        help='The columns to include from the chosen layer, E.g. "catalogid acqdate"')
    
    args = parser.parse_args()
    
    src = load_src(args.layer_name, where=args.where, columns=args.columns)
    selector_path = os.path.abspath(args.selector_path)
    print(selector_path)
    selection = make_selection(args.selector_path, src)
    out_path = os.path.join(os.path.dirname(args.selector_path), os.path.basename(args.selector_path).split('.')[0])
    out_name = out_path + '_selection.shp'
    selection.to_file(out_name, driver='ESRI Shapefile')
