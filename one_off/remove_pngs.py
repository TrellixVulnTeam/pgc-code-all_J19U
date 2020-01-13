# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 10:47:55 2020

@author: disbr007
"""

import os
from tqdm import tqdm

# Collect 10m DEM stack count tifs
parent_dir = r'V:\pgc\data\scratch\claire\pgc\arcticdem\mosaic\2m_v4'
suffix = r'10m_N_cmap.png'
pngs = []
for root, dirs, files in os.walk(parent_dir, topdown=True):
    dirs[:] = [d for d in dirs if d != 'subtiles']
    for f in files:
        if f.endswith(suffix):
            pngs.append(os.path.join(root, f))
            
for png in tqdm(pngs):
    os.remove(png)
