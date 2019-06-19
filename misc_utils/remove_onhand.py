# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 16:31:51 2019

@author: disbr007
"""

import geopandas as gpd
import os, argparse
from id_parse_utils import read_ids, write_ids


sel_path = r''

def remove_mfp(sel_path, catid='catalogid'):
    '''
    Removes any ids in the master footprint from a given .txt or .shp
    '''
    
    mfp_ids = read_ids(r'C:\pgc_index\catalog_ids.txt')

    ## Load selection method
    ext = os.path.basename(sel_path).split('.')[1]
    out_path = os.path.join(os.path.dirname(sel_path), os.path.basename(sel_path).split('.')[0])
    
    # If text, remove ids
    if ext == 'txt':
        sel_ids = read_ids(sel_path)
        cleaned = set(sel_ids) - set(mfp_ids)
        out_name = out_path + '_cleaned.txt'
        write_ids(cleaned, out_name)

    # If .shp, load gdf, then clean
    elif ext == 'shp':
        driver = 'ESRI Shapefile'
        sel = gpd.read_file(sel_path, driver=driver)
        cleaned = sel[~sel[catid].isin(mfp_ids)]
        out_name = out_path + '_cleaned.shp'
        cleaned.to_file(out_name, driver=driver)
        
    else:
        cleaned = None
        print('Unknown file format. Supported formats: .txt and .shp')
        
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', type=str,
                        help='Path to source txt or shp to be cleaned.')
    parser.add_argument('--catid', type=str, default='catalogid',
                        help='catalogid field name. defaults to "catalogid".')
    
    args=parser.parse_args()
    
    remove_mfp(args.source_path, catid=args.catid)

