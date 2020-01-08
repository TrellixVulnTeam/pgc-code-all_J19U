# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 13:14:23 2020

@author: disbr007
"""

import os
import time
import sys

import geopandas as gpd
from tqdm import tqdm, trange

from id_parse_utils import mfp_ids, compare_ids, read_ids, write_ids
from query_danco import query_footprint


#
PRJ_DIR = r'E:\disbr007\imagery_orders\missing_ids'
MONO_IDS_ALL = os.path.join(PRJ_DIR, 'polar_mono_ids.txt')
RESUME_YEAR = '2012'
RESUME_MONTH = '03'

# Load all IDs in master footprint
mfp_ids = mfp_ids()


# Load IDs we should have based on search type
# Polar - Mono - cc20
# Load regions
regions = query_footprint('pgc_polar_regions')
polar = regions[regions.loc_name.isin(['Antarctica', 'ABoVE Polar', 'Arctic'])]

# Check if resume arguments provided, if so, read the previously written IDs
if RESUME_YEAR or RESUME_MONTH:
    polar_mono_ids = read_ids(os.path.join(PRJ_DIR, 'polar_mono_ids{}-{}.txt'.format(RESUME_YEAR, RESUME_MONTH)))
else:
     polar_mono_ids = []


# Loop months and years, selecting from master DG danco footprint
for y in trange(1999, 2020, desc='Years'):
    if y < int(RESUME_YEAR):
        continue
    for m in trange(1,13, desc='Months'):
        # Redo the most recent month as it was interupted mid-run - taking set later to remove DUPs
        if m < int(RESUME_MONTH)-1:
            continue
        m = str(m)
        if len(m) == 1:
            m = '0{}'.format(m)
        where="""(acqdate LIKE '{}-{}-%%') AND (cloudcover <= 20)""".format(y, m)
        got_month_ids = False
        ct = 0
        while got_month_ids == False:
            try:
                month_ids = query_footprint('index_dg',
                                            columns=['catalogid'],
                                            where=where)
                got_month_ids = True
            except Exception as e:
                print(e)
                print('Exception occured. Sleeping for 10 seconds and retrying...')
                time.sleep(10)
                ct += 1
                if ct == 10:
                    write_ids(polar_mono_ids, os.path.join(PRJ_DIR, 'polar_mono_ids{}-{}.txt'.format(y, m)))
                    sys.exit()
        # Select only those in polar regions
        if month_ids is not None and len(month_ids) != 0:
            
            polar_month_ids = gpd.sjoin(month_ids, polar)
            polar_month_ids.drop_duplicates(subset=['catalogid'], inplace=True)
            polar_mono_ids.extend(list(polar_month_ids['catalogid']))

polar_mono_ids = list(set(list(polar_mono_ids)))
write_ids(polar_mono_ids, MONO_IDS_ALL)

# Global - Stereo - cc30


# Compare lists