# -*- coding: utf-8 -*-
"""
Created on Thu Mar 21 09:57:17 2019

@author: disbr007

xtrack not on hand ordering
"""

import geopandas as gpd
import pandas as pd
from query_danco import query_footprint

def xtrack_not_onhand():
    xtrack = query_footprint('dg_imagery_index_xtrack_cc20')
    oh = query_footprint('dg_imagery_index_all_onhand_cc20')
    xtrack_noh = xtrack[~xtrack.catalogid1.isin(oh.catalogid)]
    return xtrack_noh

def identify_platforms(df, catid='catalogid'):
    platform_codes = {
                '101': 'QB02',
                '102': 'WV01',
                '103': 'WV02',
                '104': 'WV03',
                '104A': 'WV03-SWIR',
                '105': 'GE01',
                '106': 'IK01'
                }

    df['platform'] = df[catid].str.slice(0,3).map(platform_codes).fillna('unk')
    return df

def select_platform(df, platform, min_area=None, max_area=None):
    platform_df = df[df.platform == platform]
    if min_area and max_area:
        platform_df = df[df.sqkm >= min_area & df.sqkm <= max_area]
    elif min_area:
        platform_df = df[df.sqkm >= min_area]
    elif max_area:
        platform_df = df[df.sqkm <= max_area]
    else:
        pass
    return platform_df

xtrack_noh = xtrack_not_onhand()
identify_platforms(xtrack_noh, catid='catalogid1')
wv01_noh = select_platform(xtrack_noh, 'WV01', min_area=1000, max_area=None)

lam_EA = '+proj=aea +lat_1=29.5 +lat_2=42.5'
xtrack_noh = xtrack_noh.to_crs(lam_EA)

print(xtrack_noh.area.min())
print(xtrack_noh.area.max())

platforms = xtrack_noh.platform.unique()
noh_by_platform = {}
for platform in platforms:
    noh_by_platform[platform] = xtrack_noh[xtrack_noh.platform == platform]


