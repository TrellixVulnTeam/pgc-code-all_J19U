# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 09:10:22 2020

@author: disbr007
"""

import os
from cProfile import Profile
from pstats import Stats

prof = Profile()
# Don't time imports
prof.disable()
# Import main function to run
from dem_utils import dem_valid_data
# Set output directories for profile stats
profile_dir = r'E:\disbr007\umn\ms\scratch'
stats = os.path.join(profile_dir, '{}.stats'.format(__name__))
profile_txt = os.path.join(profile_dir, '{}_profile.txt'.format(__name__))
# Turn timing back on
prof.enable()

DEMS_PATH = r'E:\disbr007\umn\ms\scratch\banks_dems_multispec_test_5.shp'
OUT_SHP = r'E:\disbr007\umn\ms\scratch\banks_dems_multispec_test_5_vp.shp'
PRJ_DIR = r'E:\disbr007\umn\ms\scratch'
SCRATCH_DIR= r'E:\disbr007\umn\ms\scratch'
LOG_FILE = r'E:\disbr007\umn\ms\scratch\vp_profile_5.log'
PROCESSED = r'E:\disbr007\umn\ms\scratch\vp_processed_5.txt'

dem_valid_data.main(DEMS_PATH=DEMS_PATH,
                    OUT_SHP=OUT_SHP,
                    PRJ_DIR=PRJ_DIR,
                    SCRATCH_DIR=SCRATCH_DIR,
                    LOG_FILE=LOG_FILE,
                    PROCESSED=PROCESSED)

prof.disable()

prof.dump_stats(stats)

with open(profile_txt, 'wt') as output:
    stats = Stats(stats, stream=output)
    stats.sort_stats('cumulative', 'time')
    stats.print_stats()