# -*- coding: utf-8 -*-
"""
Created on Fri Jan  3 14:38:09 2020

@author: disbr007
Match directory structure from one folder to another
"""

import os
import shutil
from tqdm import tqdm

print('Starting moves...')
good_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\raw'
update_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho'

# Create dictionary of filenames and correct first level up parent directory
master_loc = {}
print('Parsing good directory structure...')
for root, dirs, files in os.walk(good_dir):
    # print(len(files))
    for f in files:
        if f.endswith(('tif', 'ntf')) and r'WV02_20130708224857_10300100242C6200_13JUL08224857-P1BS-500124691090_01_P009' in f:
            print(f)
            fn = os.path.basename(f).split('.')[0]
            master_loc[fn] = []

    for f in files:
        if f.endswith(('tif', 'ntf')) and r'WV02_20130708224857_10300100242C6200_13JUL08224857-P1BS-500124691090_01_P009' in f:
            print(f)
            fn = os.path.basename(f).split('.')[0]
            fp = os.path.join(root, f)
            print(fp)
            f_sdir = os.path.basename(os.path.dirname(fp))
            print(f_sdir)
            if f_sdir not in master_loc[fn]:
                master_loc[fn].append(f_sdir)
            print('-----')

# Loop through update dir files and move to correct subdir
# Get all unique filenames in update_dir
# update_dir_files = os.listdir(update_dir)
# ud_fnames = set([os.path.basename(x).split('.')[0] for x in update_dir_files])

# print('Parsing incorrect directory and moving...')
# for root, dirs, files in os.walk(update_dir):
#     # pbar = tqdm(files)
#     for f in files:
#         print(f)
#         # Get the full path as the src of the move
#         fp = os.path.join(root, f)
#         # Get the file name to look up destinations in master_loc
#         fname = os.path.basename(f).split('.')[0]
#         fname = fname.replace('_u08mr3338', '')
#         # Get the list of destinations
#         all_matching_subdirs = set(master_loc[fname])
#         print(all_matching_subdirs)
#         # Iterate over all destinations for fp and copy it to them
#         for new_subdir in all_matching_subdirs:
#             print(new_subdir)
#             new_dir = os.path.join(update_dir, new_subdir)
#             if not os.path.exists(new_dir):
#                 os.makedirs(new_dir)
#             new_loc = os.path.join(new_dir, f)
            
#             # pbar.set_description('{}\n>>>\n{}'.format(fp, new_loc))
#             # print('Moving\n{}\n>>>\n{}'.format(fp, new_loc))
#             # shutil.copy2(fp, new_loc)