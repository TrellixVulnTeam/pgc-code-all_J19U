# -*- coding: utf-8 -*-
"""
Created on Wed Aug  7 13:44:36 2019

@author: disbr007
"""

import geopandas as gpd
import numpy as np

from id_parse_utils import compare_ids, read_ids
from query_danco import query_footprint


#### Loading
print('Loading onhand not proc.')
oh_np = gpd.read_file(r'V:\pgc\data\scratch\steve\setsm\rema_xtrack_20190805\pgcImagerIndexV6_2019jun06_antarctic_xtrack.shp',
                      driver='ESRI Shapefile')

print('Loading onhand proc.')
oh_p = gpd.read_file(r'V:\pgc\data\scratch\steve\setsm\rema_xtrack_20190805\rema_xtrack_20190805.gdb',
                     driver='OpenFileGDB',
                     layer='rema_all_completed_20190805')

print('Loading DG REMA xtrack.')
dg_xt = query_footprint('dg_imagery_index_xtrack_cc20', 
                     where="project = 'REMA'",)
#                     columns=['pairname'])

mfp_ids = read_ids(r'C:\pgc_index\catalog_ids.txt')

#### Reduce to just pairnames
oh_np_pns = set(oh_np['pairname'].unique())
oh_p_pns = set(oh_p['pairname'].unique())
dg_xt_pns = set(dg_xt['pairname'].unique())


#### Comparing
noh = dg_xt_pns - oh_p_pns - oh_np_pns



#### Full attributes
noh_geoms = dg_xt[dg_xt['pairname'].isin(noh)]


noh_geoms['left_only'] = np.where( (noh_geoms['catalogid1'].isin(mfp_ids) & ~noh_geoms['catalogid2'].isin(mfp_ids) ), 1, 0)
noh_geoms['right_only'] = np.where( (noh_geoms['catalogid2'].isin(mfp_ids) & ~noh_geoms['catalogid1'].isin(mfp_ids) ), 1, 0)
noh_geoms['both'] = np.where( (noh_geoms['catalogid1'].isin(mfp_ids) & noh_geoms['catalogid2'].isin(mfp_ids) ), 1, 0)

len_left_only = len(noh_geoms[noh_geoms['left_only'] == 1])
len_right_only = len(noh_geoms[noh_geoms['right_only'] == 1])
both = len(noh_geoms[noh_geoms['both'] == 1])

print("""
      Only left onhand = {}
      Only right onhand = {}
      Both onhand = {}
      """.format(len_left_only, len_right_only, both))

dg_xt['onhand'] = np.where( (dg_xt['catalogid1'].isin(mfp_ids) & dg_xt['catalogid2'].isin(mfp_ids)), 1, 0)

print('Xtrack onhand = {}'.format(len(dg_xt[dg_xt['onhand'] == 1] ) ) )