# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 11:33:39 2020

@author: disbr007
"""

import os
from copy import deepcopy

import geopandas as gpd

def count_ext(input_dir, ext):
    ctr = 0
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            if f.endswith(ext):
                ctr +=1
        
        # all_files = deepcopy(files)
        # fps = [os.path.join(root, f) for f in all_files]
        # matches = [f for f in all_files if f.endswith(ext)]
    print('Matches for "{}" in {}: {}'.format(ext, input_dir, ctr))
    
    return ctr


raw = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\raw'
ortho = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho'
clipped = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\clipped_copy'

raw_ct = count_ext(raw, 'ntf')
ortho_ct = count_ext(ortho, 'tif')
clipped_ct = count_ext(clipped, 'tif')


# mfp = gpd.read_file(r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\mfp_scene_ids.shp')
