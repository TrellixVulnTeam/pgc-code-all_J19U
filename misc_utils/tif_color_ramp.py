# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 14:13:57 2020

@author: disbr007
"""

import argparse
import os
import subprocess



# Inputs
parent_dir = r'V:\pgc\data\scratch\claire\pgc\arcticdem\mosaic\2m_v4\38_01'
color_map = r'cmap.txt'

for root, dirs, files in os.walk(parent_dir):
    stack_count_tifs = []
    for f in files:
        if f.endswith('_N.tif'):
            stack_count_tifs.append(os.path.join(root, f))
            
for tif in stack_count_tifs:
    # tif_dir = os.path.dirname(tif)
    # tif_name = os.path.basename(tif).split('.')[0]
    # png_out = '{}_cmap.png'.format(tif_name)
    # cmd = ['gdaldem', 'color-relief', tif, png_out, '-nearest_color_entry', '-of PNG', 'alpha']
    # print(cmd)
    print(tif)





