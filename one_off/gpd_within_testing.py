# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 09:57:20 2019

@author: disbr007
"""

import geopandas as gpd
from tqdm import tqdm
from query_danco import query_footprint

tqdm.pandas()
it = query_footprint('dg_imagery_index_stereo_cc20', where="y1 > 45", columns=['pairname', 'acqdate', 'sqkm_utm'])
test = it[0:20000]

arc = query_footprint('pgc_polar_regions', where="loc_name = 'Arctic'", columns=['loc_name'])


def find_within(region, row):
    '''
    Determines if each row's geometry is within the given region geometry
    '''
    row_geom = row.geom.centroid

    return row_geom.within(region)

region = arc.geometry[0]

test['in'] = test.progress_apply(lambda x: find_within(region, x), axis=1)