# -*- coding: utf-8 -*-
"""
Created on Fri Jan  3 14:38:09 2020

@author: disbr007
Match directory structure from one folder to another
"""

import os
import shutil
from tqdm import tqdm, trange

print('Starting moves...')
good_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\raw'
update_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho'

# Create dictionary of filenames and correct first level up parent directory
master_loc = {}
print('Parsing good directory structure...')
for root, dirs, files in os.walk(good_dir):
    for f in files:
        fn = os.path.basename(f).split('.')[0]
        fp = os.path.join(root, f)
        f_sdir = os.path.basename(os.path.dirname(fp))
        master_loc[fn] = f_sdir


# Loop through update dir files and move to correct subdir
# Get all unique filenames in update_dir
# update_dir_files = os.listdir(update_dir)
# ud_fnames = set([os.path.basename(x).split('.')[0] for x in update_dir_files])

print('Parsing incorrect directory and moving...')
for root, dirs, files in os.walk(update_dir):
    pbar = tqdm(files)
    for f in pbar:
        fp = os.path.join(root, f)
        fname = os.path.basename(f).split('.')[0]
        fname = fname.replace('_u08mr3338', '')
        new_subdir = master_loc[fname]
        new_dir = os.path.join(update_dir, new_subdir)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        new_loc = os.path.join(new_dir, f)
        
        pbar.set_description('{}\n>>>\n{}'.format(fp, new_loc))
        # print('Moving\n{}\n>>>\n{}'.format(fp, new_loc))
        shutil.move(fp, new_loc)