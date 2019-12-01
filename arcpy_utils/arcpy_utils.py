# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 10:45:25 2019

@author: disbr007
"""

import logging

import arcpy

from id_parse_utils import pgc_index_path


#### Logging setup
# create logger
logger = logging.getLogger('arcpy-utils')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


arcpy.env.overwriteOutput = True

MFP_PATH = pgc_index_path()

def load_pgc_index(mfp_path=MFP_PATH, where=None):
    """
    Loads the PGC master footprint with an optional where clause and returns 
    it as an arcpy layer object.
    
    Parameters:
    mfp_path (str): path to master footprint
    where    (str): SQL query to pass when loading master footprint
    """
    # Location in memory to save result 
    mem_lyr = r'memory/pgc_index_temp'
    if where:
        idx_lyr = arcpy.MakeFeatureLayer_management(mfp_path, mem_lyr,
                                                    where_clause=where)
    else:
        idx_lyr = arcpy.MakeFeatureLayer_management(mfp_path, mem_lyr)
    
    ## Check number returned features is not 0
    result = arcpy.GetCount_management(idx_lyr)
    count = int(result.getOutput(0))
    logger.debug('Loaded features from master footprint {}'.format(count))
    if count == 0:
        logger.warning('0 features returned from selection.')
    
    return mem_lyr