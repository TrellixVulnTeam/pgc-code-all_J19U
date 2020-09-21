# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 13:15:06 2020

@author: disbr007
"""

import os

import numpy as np
import geopandas as gpd


prj_path = r'E:\disbr007\general\geocell'

geocells_path = r'E:\disbr007\general\geocell\us_one_degree_geocells_buff150km.shp'
graticules_path = r'E:\disbr007\general\graticules\ne_10m_graticules_1.shp'


gc = gpd.read_file(geocells_path)
gc.index.name = 'geocell'
gr = gpd.read_file(graticules_path)

gc_names = gpd.sjoin(gc, gr)
gc_names.index.name = 'geocell'
agg = {'degrees': ['max']}
gb = gc_names.groupby(['geocell', 'direction']).agg(agg)
gb.reset_index(inplace=True)
gb.columns = gb.columns.droplevel(1)
gb_cols = list(gb)
# test = gb.join(gb.groupby('geocell').last(), on='geocell', rsuffix='_lon').drop_duplicates(subset=['{}_lon'.format(x) for x in gb_cols if x != 'geocell']).reset_index(drop=True)
gb = gb.pivot(index='geocell', columns='direction', values='degrees')

gc = gc.merge(gb, on='geocell')


def box_name(N, E, S, W):
    if not np.isnan(N):
        lat = 'n{}'.format(int(N))
    elif not np.isnan(S):
        lat = 's{}'.format(int(S))
    else:
        lat = ''
    if not np.isnan(E):
        lon = 'e{}'.format(int(E))
    elif not np.isnan(W):
        lon = 'w{}'.format(int(W))
    else:
        lon = ''

    return '{}{}'.format(lat, lon)
        
gc['name'] = gc.apply(lambda x: box_name(N=x['N'], E=x['E'], S=x['S'], W=x['W']), axis=1)

gc.to_file(os.path.join(prj_path, 'us_one_degree_geocells_buff150km_named.shp'))