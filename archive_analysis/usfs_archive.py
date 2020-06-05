# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 20:27:05 2020

@author: disbr007
"""

import geopandas as gpd

from selection_utils.query_danco import query_footprint, count_table, list_danco_db, layer_fields


# Params
# edem_lyr = 'pgc_earthdem_regions'
# earthdem = query_footprint(edem_lyr)

regions = ['earthdem_03_conus',
           'earthdem_04_great_lakes',
           'arcticdem_34_alaska_north',
           'arcticdem_31_alaska_south']


# Query footprints
where = """region_id IN ({})""".format(str(regions)[1:-1])
count = count_table('dg_imagery_index_stereo', where=where)

# fps = query_footprint('index_dg', )
