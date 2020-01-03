# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 06:38:02 2019

@author: disbr007
"""

import argparse
import os 

import geopandas as gpd
import pandas as pd

from query_danco import query_footprint, list_danco_db, footprint_fields


# Inputs
# PRJ_DIR = r'E:\disbr007\UserServicesRequests\Projects\jclark\4056'
# AOI_P = r'prj_files\BITE_buffers.shp'

def select_AHAP(AOI_P, repeat=False, write=None):
    # String literals
    LAYER = 'usgs_index_aerial_image_archive'
    DB = 'imagery'
    # Path to AHAP photo extents shapefile
    PHOTO_EXT_P = r'E:\disbr007\general\aerial\AHAP\AHAP_Photo_Extents\AHAP_Photo_Extents.shp'
    # Identifier in AHAP photos shp
    PHOTO_ID = 'PHOTO_ID'
    # Identified in AHAP photos table
    UNIQUE_ID = 'unique_id'
    
    
    # Load danco AHAP imagery table
    aia = query_footprint(LAYER, db=DB, table=True, where="campaign = 'AHAP'")
    # Load photo extents
    PHOTO_EXT = gpd.read_file(PHOTO_EXT_P)
    
    # Load AOI and match crs
    AOI = gpd.read_file(os.path.join(AOI_P))
    AOI = AOI.to_crs(PHOTO_EXT.crs)
    
    # Select Photo Extents by intersection with AOI polygons
    selection = gpd.sjoin(PHOTO_EXT, AOI, how='inner', op='intersects')
    
    # Remove duplicate Photo Extents if specified
    if repeat is False:
        selection = selection.drop_duplicates(subset=PHOTO_ID)
    
    # Join to table with filenames
    selection = pd.merge(selection, aia, how='left', 
                         left_on=PHOTO_ID, right_on=UNIQUE_ID)
    
    # Write out shapefile
    if write is not None:
        selection.to_file(write)
    
    return selection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('AOI', type=os.path.abspath,
                        help='Path to AOI shapefile.')
    parser.add_argument('-o', '--output', type=os.path.abspath,
                        help='''Output selection of AHAP photo extents.''')
    parser.add_argument('-r', '--repeat', action='store_true',
                        help='''Use flag to specify repeat extents should be 
                                included, in the case of an extent overlapping 
                                multiple AOI polygons.''')
