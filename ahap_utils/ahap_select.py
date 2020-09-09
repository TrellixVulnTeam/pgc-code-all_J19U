# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 06:38:02 2019

@author: disbr007
Select AHAP footprints that overlap the given AOI.
"""

import argparse
import logging
import os 

import geopandas as gpd
import pandas as pd

from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import read_ids

# create logger with 'spam_application'
logger = logging.getLogger('ahap_select')
logger.setLevel(logging.INFO)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def select_AHAP(PHOTO_IDS=None, AOI_P=None, resolution=None,
                repeat=False, write=None):
    # String literals
    LAYER = 'usgs_index_aerial_image_archive'
    DB = 'imagery'
    # Path to AHAP photo extents shapefile
    PHOTO_EXT_P = r'E:\disbr007\general\aerial\AHAP\AHAP_Photo_Extents\AHAP_Photo_Extents.shp'
    # Identifier in AHAP photos shp
    PHOTO_ID = 'PHOTO_ID'
    # Identified in AHAP photos table
    UNIQUE_ID = 'unique_id'
    SERIES = 'series'
            
    
    # Load danco AHAP imagery table
    logger.info('Reading AHAP danco table')
    where = "campaign = 'AHAP"
    if resolution:
        where += "series = '{}'".format(resolution)
    aia = query_footprint(LAYER, db=DB, table=True, where="campaign = 'AHAP'")

    # Load photo extents
    logger.info("Loading AHAP photo extent shapefile...")
    PHOTO_EXT = gpd.read_file(PHOTO_EXT_P)
    
    if AOI_P:
        logger.info('Reading AOI shapefile....')
        # Load AOI and match crs
        AOI = gpd.read_file(os.path.join(AOI_P))
        AOI = AOI.to_crs(PHOTO_EXT.crs)
        
        
        logger.info('Selecting AHAP imagery by location...')
        # Select Photo Extents by intersection with AOI polygons
        selection = gpd.sjoin(PHOTO_EXT, AOI, how='inner', op='intersects')
    elif PHOTO_IDS:
        if os.path.isfile(PHOTO_IDS[0]):
            ids = read_ids(PHOTO_IDS[0])
        elif isinstance(PHOTO_IDS, list):
            ids = PHOTO_IDS
        selection = PHOTO_EXT[PHOTO_EXT[PHOTO_ID].isin(ids)]
    
    # Remove duplicate Photo Extents if specified
    if repeat is False:
        selection = selection.drop_duplicates(subset=PHOTO_ID)
    
    
    # Join to table with filenames
    selection = pd.merge(selection, aia, how='left', 
                         left_on=PHOTO_ID, right_on=UNIQUE_ID)
    

    logger.info('Selected features found: {:,}'.format(len(selection)))

    # Write out shapefile
    if write is not None:
        logger.info('Writing AHAP selection to: {}'.format(write))
        selection.to_file(write)
    
    return selection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--PHOTO_IDS', nargs='+',
                        help='Path to photo_ids list or space seperated IDs')
    parser.add_argument('--AOI', type=os.path.abspath,
                        help='Path to AOI shapefile.')
    parser.add_argument('-o', '--output', type=os.path.abspath,
                        help='''Output selection of AHAP photo extents.''')
    parser.add_argument('-res', '--resolution', type=str, choices=['high_res', 'medium_res'],
                        help='Resolution to select.')
    parser.add_argument('-r', '--repeat', action='store_true',
                        help='''Use flag to specify repeat extents should be 
                                included, in the case of an extent overlapping 
                                multiple AOI polygons.''')
                                
    args = parser.parse_args()
    
    select_AHAP(PHOTO_IDS=args.PHOTO_IDS, AOI_P=args.AOI,
                resolution=args.resolution,
                repeat=args.repeat, write=args.output)
