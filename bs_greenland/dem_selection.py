# -*- coding: utf-8 -*-
"""
Created on Thu Dec 12 12:07:09 2019

@author: disbr007
Select DEM footprints that intersect AOI vector file.
"""

import argparse
import logging
import os

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

from query_danco import query_footprint, layer_crs
from select_danco import select_danco, build_where



#### Logging setup
logger = None # Remove any logger's from previous runs
logger = logging.getLogger('dem_selection')
logger.propagate = False
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

## INPUTS
AOI_PATH = r'E:\disbr007\UserServicesRequests\Projects\kbollen\TerminusBoxes\GreenlandPeriph_BoxesUpdated.shp'
# Identifying field for individual features in AOI - this will allow repeat footprints
# if the footprint is in multiple features
AOI_FEAT = 'BoxID'


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

    #### WRITE SELECTION
    if out_path is not None:
        dems.to_file(out_path)
    
    return dems


## Select all DEMs over AOI features, allowing for repeats
dems = select_dems(AOI_PATH, out_path=None, aoi_feat=AOI_FEAT)



# if __name__ == '__main__':
#     parser = argparse.ArgumentParser()
    
#     parser.add_argument('aoi', type=str,
#                         help='Path to aoi vector file.')
#     parser.add_argument('--out_path', type=str,
#                         help='Path to write selected DEMs to.')
    
#     args = parser.parse_args()
    
#     select_dems(args.aoi, args.out_path)
    