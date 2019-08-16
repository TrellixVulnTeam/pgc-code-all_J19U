# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:59:08 2019

@author: disbr007
"""

import os
import pandas as pd
import pandas_profiling
import geopandas as gpd

from id_parse_utils import read_ids, write_ids, compare_ids
from ids_order_sources import get_ordered_ids
from query_danco import query_footprint, stereo_noh
from dataframe_plotting import plot_timeseries_stacked


def locate_id(each_id, pgc_ids, nasa_ids, ordered_ids):
    '''
    Returns a where an id is located
    '''
        
    if each_id in pgc_ids:
        location = 'pgc'
    elif each_id in nasa_ids:
        location = 'nasa'
    elif each_id in ordered_ids:
        location = 'ordered'
    else:
        location = 'unknown'
    return location


prj_dir = r'C:\temp\missing_cc20'
fp_name = 'dg_imagery_index_stereo'

#### Load all cc20 stereo imagery
where = """cloudcover >=0 and cloudcover <= 20 and acqdate <= '2019-08-03'"""

print('loading footprint...')
fp = query_footprint(fp_name,
                     where=where, 
                     columns=['catalogid', 'stereopair', 'cloudcover', 'acqdate'])

#### Load AOI regions and sjoin
#print('performing sjoin...')
#aoi = gpd.read_file(r'E:\disbr007\imagery_orders\all_regions.shp', driver='ESRI Shapefile')
#fp = gpd.sjoin(fp, aoi, how='inner')


print('loading id lists')
pgc_ids = set(read_ids(r'C:\pgc_index\catalog_ids.txt')) #mfp
nasa_ids = set(read_ids(r'C:\pgc_index\nga_inventory_canon20190505\nga_inventory_canon20190505_CATALOG_ID.txt'))
ordered_ids = set(get_ordered_ids()) #order sheets


#### Locate each ID at NASA, PGC, or ordered, or 'missing'
fp['location'] = fp['catalogid'].apply(lambda x: locate_id(x, pgc_ids, nasa_ids, ordered_ids))


missing_fp = fp[fp['location'] == 'unknown']


profile = pandas_profiling.ProfileReport(missing_fp)

#### Plotting 
dfc_agg, percentage = plot_timeseries_stacked(fp, 'acqdate', 'catalogid', category_col='location', freq='M', percentage=True)
dfc_agg, percentage = plot_timeseries_stacked(fp, 'acqdate', 'catalogid', category_col='location', freq='M', percentage=False)




print('writing outputs...')
out_name = 'stereo_cc20_2019aug04'

#fp[fp['catalogid'].isin(ids_noh) | fp['stereopair'].isin(ids_noh)].to_file(os.path.join(prj_dir, '{}.shp'.format(out_name)))
#write_ids(list(ids_noh), os.path.join(prj_dir, '{}.txt'.format(out_name)))



