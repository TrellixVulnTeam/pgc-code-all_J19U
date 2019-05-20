# -*- coding: utf-8 -*-
"""
Created on Mon May 20 15:17:24 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

sys.path.insert(0,'C:\code\misc_utils')
from id_parse_utils import write_ids

driver = 'ESRI Shapefile'

onhand_path = r"E:\disbr007\UserServicesRequests\Projects\1539_CIRES_Herzfeld\3740\3740_onhand.shp"
onhand = gpd.read_file(onhand_path, driver=driver)

file_paths = list(onhand.S_FILEPATH)

write_ids(file_paths, os.path.join(os.path.dirname(onhand_path), '3740_onhand_paths.txt'))