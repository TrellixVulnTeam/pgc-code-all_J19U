o# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 16:31:38 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from query_danco import query_footprint
from id_parse_utils import read_ids

print('Loading intrack stereo cc50...')
it = query_footprint('dg_imagery_index_stereo', where='cloudcover <= 50')

print('Loading processed pairnames...')
proc_ids = read_ids(r"V:\pgc\data\scratch\erik\projects\gn\dg_stereo_2019jul02\select\global_pairs_complete_and_in_progress_all_20190702.csv")
it['processed'] = np.where(it.pairname.isin(proc_ids), 'Yes', 'No')

print('Loading stereo onhand...')
pgc = query_footprint('dg_imagery_index_stereo_onhand', where='cloudcover <= 50', columns=['catalogid', 'stereopair'])
oh_pgc = set(list(pgc['catalogid']) + list(pgc['stereopair']))
del pgc
print('Loading adapt onhand...')
adapt = read_ids(r'C:\pgc_index\adapt_ids.txt')
oh_adp = set(list(adapt))
del adapt
oh_ids = oh_pgc.union(oh_adp)

it['onhand'] = np.where((it.catalogid.isin(oh_ids)) & (it.stereopair.isin(oh_ids)), 'Yes', 'No')
print('Writing shapefile...')
out_path = r'C:\temp\intrack_pairs_cc50_status.shp'
it.to_file(out_path, driver='ESRI Shapefile')
