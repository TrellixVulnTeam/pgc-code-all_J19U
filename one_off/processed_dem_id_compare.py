# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 12:54:37 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import sys, os
sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids, write_ids

project_path =  r"E:\disbr007\UserServicesRequests\Projects\1521_spergel\3699\project_files"

#processed_path = r"V:\pgc\data\elev\dem\setsm\ArcticDEM\region\pairs_complete_greenland_20190403.txt" # Greenland
#processed_path = r"V:\pgc\data\elev\dem\setsm\REMA\region\pairs_complete_all_8m_20190412.txt" # REMA 8m
processed_path = r"V:\pgc\data\elev\dem\setsm\REMA\region\pairs_complete_all_2m_20190412.txt" # REMA 2m
processed = read_ids(processed_path)

dems_path = os.path.join(project_path, "DEM_possibilities.shp")

dems = gpd.read_file(dems_path, driver='ESRI Shapefile')

processed_dems = [x for x in dems['pairname'] if x in processed]
not_proc_dems = [x for x in dems['pairname'] if x not in processed]

out_proc = os.path.join(project_path, 'proc_dems.txt')
#write_ids(processed_dems, out_proc)

out_not = os.path.join(project_path, 'not_proc_dems.txt')
#write_ids(not_proc_dems, out_not)
