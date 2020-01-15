# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 15:19:16 2020

@author: disbr007
"""
import argparse
import os
import shutil
import subprocess
from tqdm import tqdm

import geopandas as gpd
from id_parse_utils import write_ids, parse_filename
from clip2shp_bounds import warp_rasters

def windows2linux(src):
    out_path = src.replace('\\', '/')
    out_path = out_path.replace('V:', '/mnt')
    return out_path

# # Path to footprints
fp_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056\prj_files\mfp_selection_2020jan07_BITE_sel.shp'
# Path to AOIs
aois_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056\prj_files\BITE_buffers.shp'
# Field in AOIs that is unique to each aoi
aoi_unique_id = 'subfolder'
# Folder holding imagery
ortho = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho'
# Folder to move imagery to
out_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\ortho_selected'

# Load shapefiles
aois = gpd.read_file(aois_p)
fps = gpd.read_file(fp_p)

if aois.crs != fps.crs:
    aois = aois.to_crs(fps.crs)

master = gpd.sjoin(fps, aois, how='left')

# Subset and move
# Get all scene ids in 
scene_ids = list(master['scene_id'])

for sd in aois[aoi_unique_id].unique():
    with open(os.path.join(out_dir, '{}.txt'.format(sd)), 'w') as f:
        pass

# Loop over files in ortho
for f in tqdm(os.listdir(ortho)):
    # Get scene ID of file
    sid = parse_filename(f, 'scene_id',)
    if sid in scene_ids:
        # Get all destinations
        dst_subfolders = list(master[master['scene_id']==sid]['subfolder'])
        dst_subfolders = [str(x) for x in dst_subfolders]
        for dst_sd in dst_subfolders:
            dst_sf = os.path.join(out_dir, dst_sd)
            if not os.path.exists(dst_sf):
                os.makedirs(dst_sf)
            src = os.path.join(ortho, f)
            dst = os.path.join(dst_sf, f)
            # convert to linux path
            src = windows2linux(src)
            dst = windows2linux(dst)
            
            with open(os.path.join(out_dir, '{}.txt'.format(dst_sd)), 'a') as f_list:
                f_list.write(src)
                f_list.write('\n')
            print('Moving: {}\n-->\n{}\n\n'.format(src, dst))
            # if not os.path.exists(dst):
                # shutil.copy2(src, dst)
            