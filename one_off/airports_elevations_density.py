# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 16:31:51 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os, argparse


ap_path = r"E:\disbr007\imagery_archive_analysis\density\airport\ak_airports.txt"

with open(ap_path, 'r') as f:
    content = f.readlines()
    
    lat = []
    lon = []
    elv = []
    apc = []
    
    for line in content:
        # seperate by spaces - variable number between elements
        line_lst = line.split(' ')
        # removes empty strings
        line_lst = [x.rstrip("\n\r") for x in line_lst if x != '']
        # Assign each element to appropriate dict col
        for elem in line_lst:
            lat.append(line_lst[0])
            lon.append(line_lst[1])
            elv.append(line_lst[2])
            apc.append(' '.join(line_lst[3:]))
            
ap_dict = {'lat': lat, 'lon': lon, 'elv': elv, 'apc': apc}

ap = pd.from_dict(ap_dict)
            
    