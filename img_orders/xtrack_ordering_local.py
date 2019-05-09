# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 16:52:40 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import sys

from query_danco import query_footprint

sys.path.insert(0, r'C:\code\img_orders')
from imagery_order_sheet_maker_module import create_sheets



def identify_platforms(df, catid='catalogid'):
    '''
    creates a new column 'platform', which indicates the platform of the catalogid column
    specified. 
    df = dataframe containing catalog ids
    catid = catalogid column to parse (e.g. 'catalogid', 'catalogid1', "CATALOG_ID')
    '''
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
    '''
    selects only the specified platform and ids within area range
    df: dataframe to select from, must contain 'platform' column
    platform: platform to select ['WV01', 'WV02', 'WV03', 'GE01', 'IK01']
    min_area = smallest area to select
    max_area = largest area to select
    '''
    
    platform_df = df[df.platform == platform]
    if min_area and max_area:
        platform_df = platform_df[platform_df.sqkm >= min_area & platform_df.sqkm <= max_area]
    elif min_area:
        platform_df = platform_df[platform_df.sqkm >= min_area]
    elif max_area:
        platform_df = platform_df[platform_df.sqkm <= max_area]
    else:
        pass
    return platform_df


xtrack_path = r"C:\Users\disbr007\pgc_index\pgcImageryIndex_xtrack_cc20.gdb"

driver = 'OpenFileGDB'
xtrack = gpd.read_file(xtrack_path, driver=driver, layer='dg_imagery_index_xtrack_cc20_prjEA')

oh = query_footprint('dg_imagery_index_all_onhand_cc20')
xtrack_noh = xtrack[~xtrack.catalogid1.isin(oh.catalogid)]

identify_platforms(xtrack_noh, catid='catalogid1')

#x_noh_WV01 = xtrack_noh[xtrack_noh.platform == 'WV01']
#x_noh_WV01_1k = x_noh_WV01[x_noh_WV01.sqkm > 1000]

x_noh_WV01 = select_platform(xtrack_noh, 'WV01', min_area=1000)
#x_noh_WV01.sort_values('acqdate1', inplace=True)
x_noh_WV01_pre2014 = x_noh_WV01[x_noh_WV01.acqdate1 < '2014']
x_noh_WV02 = select_platform(xtrack_noh, 'WV02', min_area=1000)
#x_noh_WV02.sort_values('acqdate1', inplace=True)
x_noh_WV02_pre2014 = x_noh_WV02[x_noh_WV02.acqdate1 < '2014']

x_noh_order = pd.concat([x_noh_WV01_pre2014, x_noh_WV02_pre2014], sort=True)
x_noh_order['catalogid'] = x_noh_order['catalogid1']

with pd.ExcelWriter('E:\disbr007\imagery_orders\PGC_order_2019apr24_crosstrack_1k_WV01_WV02\master_crosstrack_WV01_02_1k.xlsx') as writer:
    x_noh_order.to_excel(writer, sheet_name='Sheet_1')

#create_sheets(x_noh_order, 'WV01_02_1k')



