# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 16:20:46 2019

@author: disbr007
Get all ids from mfp by looping through slices of mfp
"""

import os, tqdm
import fiona
import geopandas as gpd
import multiprocessing
from joblib import Parallel, delayed
from id_parse_utils import write_ids

def main():
    # Path to mfp
    mfp = r'C:\pgc_index\pgcImageryIndexV6_2019jun06.gdb'
    mfp_name = 'pgcImageryIndexV6_2019jun06'
    
    mfp_layers = fiona.listlayers(mfp)
    mfp_layers.remove(mfp_name)
    
    catalog_ids = []
    for layer in tqdm.tqdm(mfp_layers):
        gdf = gpd.read_file(os.path.join(mfp), driver='OpenFileGDB', layer=layer)
        layer_catids = list(set(gdf['catalog_id']))
        for each_id in layer_catids:
            catalog_ids.append(each_id)

    write_ids(set(catalog_ids), r'C:\pgc_index\catalog_ids.txt')


if __name__ == '__main__':
    main()