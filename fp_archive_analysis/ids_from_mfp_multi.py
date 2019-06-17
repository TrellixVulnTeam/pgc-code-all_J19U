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

    def get_ids(layer):
        gdf = gpd.read_file(os.path.join(mfp), driver='OpenFileGDB', layer=layer)
        layer_catids = list(set(gdf['catalog_id']))
        return layer_catids
    
    num_cores = 3
    results = Parallel(n_jobs=num_cores)(delayed(get_ids)(i) for i in tqdm.tqdm(mfp_layers))
    
    catalog_ids = []
    for sublist in results:
        for each_id in sublist:
            catalog_ids.append(each_id)
    
    write_ids(catalog_ids, r'C:\pgc_index\catalog_ids_multithread.txt')


if __name__ == '__main__':
    main()