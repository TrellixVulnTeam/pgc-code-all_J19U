# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 12:11:46 2019

@author: disbr007
"""

import os
import logging

from id_parse_utils import read_ids

# Args
ids_path = r'E:\disbr007\UserServicesRequests\Projects\bjones\1653\baldwin_IK01_QB02.dbf' # Text file -- add support for comparing dirs
check_dir = r'V:\pgc\userftp\bmjones\4042_2019dec10\QB02\ortho'
write = False # Write included / not included IDs to text file
id_of_int = 'CATALOG_ID' # or CATALOG_ID, SCENE_ID


# LOGGING SETUP
# Create logger
logger = logging.getLogger('id_verify')
logger.setLevel(logging.DEBUG)
# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# Add the handler to the logger
logger.addHandler(ch)


# STRING LIT
#FILENAME = 'filename'
CATALOG_ID = 'CATALOG_ID'
SCENE_ID = 'SCENE_ID'
PLATFORM = 'platform'
PROD_CODE = 'prod_code'

# LOAD SOURCE IDS
# Read in text file of IDs of interest (or shapfile, or CLI entry)
source_ids = read_ids(ids_path)
source_ids = set(source_ids)
logger.info("{}'s found in source: {}".format(id_of_int, len(source_ids)))


# samples
fname = r'QB02_20020822221714_10100100010DFC00_02AUG22221714-M1BS-052800672090_01_P001.ntf'
catid = r'10100100010DFC00'
sceid = r'QB02_20020822221714_10100100010DFC00_02AUG22221714-M1BS-052800672090_01_P001'
strid = r'QB02_10100100010DFC00_M1BS_052800672090_01'

check_dir_parsed = {}
# PARSE IDS FROM CHECK DIR
for root, dirs, files in os.walk(check_dir):
    for f in files:
        # Parse filename
        scene_id = f.split('.')[0]
        first, prod_code, third = scene_id.split('-')
        platform, date, catalogid, date_words = first.split('_')
        # Add to storage dict
#        check_dir_parsed[f] = {CATALOG_ID: [],
#                               SCENE_ID: [],
#                               PROD_CODE: [],
#                               PLATFORM: []}
        check_dir_parsed[f] = {}

        check_dir_parsed[f][CATALOG_ID] = catalogid
        check_dir_parsed[f][SCENE_ID] = scene_id
        check_dir_parsed[f][PROD_CODE] = prod_code
        check_dir_parsed[f][PLATFORM] = platform

# Get check dir ID of interest
dir_ids = []
for filename, f_dict in check_dir_parsed.items():
    dir_ids.append(f_dict[id_of_int])
dir_ids = set(dir_ids)
logger.info("{}'s found in directory: {}".format(id_of_int, len(dir_ids)))

# COMPARE







        