# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 16:36:17 2019

@author: disbr007
"""

import logging
import geopandas as gpd

from id_parse_utils import remove_mfp


logging.basicConfig(level=logging.DEBUG)
sel_p = r'E:\disbr007\UserServicesRequests\Projects\akhan\order_selection.shp'
sel = gpd.read_file(sel_p)

rem = remove_mfp(list(sel['catalogid']))