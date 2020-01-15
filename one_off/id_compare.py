# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 11:45:41 2020

@author: disbr007
"""
import os

from id_parse_utils import write_ids

import geopandas as gpd

ordered = r'E:\disbr007\UserServicesRequests\Projects\akhan\baker_illa_ids2order.shp'
baker_rec = r'E:\disbr007\UserServicesRequests\Projects\akhan\baker_order_mfp_sel.shp'
illec_rec = r'E:\disbr007\UserServicesRequests\Projects\akhan\ill_order_mfp_sel.shp'

o = gpd.read_file(ordered)
b = gpd.read_file(baker_rec)
i = gpd.read_file(illec_rec)

o_ids = set(o['catalogid'])
b_ids = set(b['catalog_id'])
i_ids = set(i['catalog_id'])

rec = b_ids.union(i_ids)

missing = o_ids - rec

write_ids(missing, os.path.join(os.path.dirname(ordered), 'missing_ids.txt'))
