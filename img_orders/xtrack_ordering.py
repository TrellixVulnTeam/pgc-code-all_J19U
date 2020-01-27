# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 13:08:08 2020

@author: disbr007
"""


from selection_utils.query_danco import query_footprint
from misc_utils.logging_utils import create_logger


# INPUTS
NUM_IDS = 40_000 # Desired number of IDs
SENSORS = ['WVO1', 'WV02', 'WV03']
MAX_AREA = 1000 # Max overlap area to include
MIN_AREA = 500 # Min overlap area to include
REGION = '' # EarthDEM region to include **NOT IMPLEMENTED**



# Load footprints
xtrack_name = 'dg_imagery_index_xtrack_cc20'
cols = ['catalogid1', 'catalogid2', 'acqdate1', 'pairname']
xt = query_footprint(xtrack_name, columns=cols, where="objectid < 100")


