# -*- coding: utf-8 -*-
"""
Created on Thu Dec 12 12:07:09 2019

@author: disbr007
Select DEM footprints that intersect AOI vector file.
"""

import argparse
import logging
import numpy as np
import os
import subprocess

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

from query_danco import query_footprint, layer_crs
from select_danco import select_danco, build_where
from logging_utils import create_logger


logger = create_logger('dem_selection', 'sh', 'INFO')

# ## INPUTS
# AOI_PATH = r'E:\disbr007\UserServicesRequests\Projects\kbollen\TerminusBoxes\GreenlandPeriph_BoxesUpdated.shp'
# # Identifying field for individual features in AOI - this will allow repeat footprints
# # if the footprint is in multiple features
# AOI_FEAT = 'BoxID'
# DST_DIR = r'C:\temp\greenland_dems'
# SEL_PATH = os.path.join(DST_DIR, 'master_dem_selection.shp')

## Using PGC copy script
# DEM_COPY_LOC = r'C:\code\cloned_repos\pgcdemtools\copy_dems.py'
# PYTHON2 = r'C:\OSGeo4W64\bin\python.exe'

## PARAMS
SUBDIR = 'subdir' # name of field containing name of subdirectory
FILEPATH = 'filepath' # field containing unix filepath
FILENAME = 'filename' # created field holding just filename
 

def select_dems(aoi_path, out_path, aoi_feat=None):
    """
    Select DEM footprints that intersect aoi. Write selection to out_path.
    
    Parameters
    ----------
    aoi_path : str
        The path to the AOI.
    out_path: str
        The path to write selection to.
    aoi_feat: str
        Identifying field in AOI. Providing this allows for repeat footprints
        if they intersect multiple AOIs.

    Returns
    -------
    Geodataframe of selection.
    """
    #### PARAMS
    DEM_FP = r'pgc_dem_setsm_strips'
    FOOTPRINT = 'footprint'
    
    
    #### LOAD AOI
    logger.info('Loading AOI...')
    aoi = gpd.read_file(aoi_path)
    aoi_original_crs = aoi.crs
    # Convert to CRS of DEM footprint
    aoi = aoi.to_crs(layer_crs(DEM_FP, FOOTPRINT))
    # Get min and max x and y of AOI for loading DEMs footprints faster
    minx, miny, maxx, maxy = aoi.geometry.total_bounds
    
    
    #### LOAD DEM footprints over AOI
    logger.info('Loading DEM footprints over AOI...')
    # Drop duplicates only if same aoi_feat and filepath
    dems = select_danco(DEM_FP,
                        selector_path=aoi_path,
                        min_x1=minx-2,
                        min_y1=miny-2,
                        max_x1=maxx+2,
                        max_y1=maxy+2,
                        drop_dup=[aoi_feat, 'filepath'])
    
    # Convert both back to original crs of AOI
    aoi = aoi.to_crs(aoi_original_crs)
    dems = dems.to_crs(aoi.crs)

    #### WRITE selection shapefile
    if out_path is not None:
        dems.to_file(out_path)
    
    return dems


def create_subdir(BoxID):
    bid = str(BoxID).zfill(3)
    first = bid[0]
    subdir = '{}00'.format(first)
    return subdir

    
# ## Select all DEMs over AOI features, allowing for repeats if overlap 
# ## multiple AOIs
# dems = select_dems(AOI_PATH, out_path=None, aoi_feat=AOI_FEAT)
# ## Create a subdirectory field, based on grouping BoxID by 100's [000, 100, etc.]
# ## TODO: decide if this is desired directory structure
# dems[SUBDIR] = dems['BoxID'].apply(lambda x: create_subdir(x))
# dems.to_file(SEL_PATH)


#### TRANSFER FILES
# for subdir in dems[SUBDIR].unique():
    subdir_dems = dems[dems[SUBDIR]==subdir]
    dst_subdir = os.path.join(DST_DIR, subdir) 
    if not os.path.exists(dst_subdir):
        os.makedirs(dst_subdir)
    ## Write selection out as shapefile
    out_shp = os.path.join(dst_subdir, 'footprint_{}.shp'.format(subdir))
    subdir_dems.to_file(out_shp)
    ## Call pgc's dem_copy.py
    cmd = """{} {} {} {} --dryrun""".format(PYTHON2, DEM_COPY_LOC, out_shp, dst_subdir)
    print(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    logger.info('Stdout: {}\n\n'.format(stdout))
    logger.info('Stderr: {}\n\n'.format(stderr))
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('aoi', type=os.path.abspath,
                        help='Path to aoi vector file.')
    parser.add_argument('out_path', type=os.path.abspath,
                        help='Path to write selected DEMs footprint to.')
    parser.add_argument('--aoi_id', type=str, default=None,
                        help='''Unique field in AOI to allow for duplicating DEMS
                                if the DEM intersects more than one AOI.''')
    
    args = parser.parse_args()
    
    select_dems(args.aoi, 
                out_path=args.out_path,
                aoi_feat=args.aoi_id)
    