# -*- coding: utf-8 -*-
"""
Created on Tue May 14 16:06:29 2019

@author: disbr007
"""

import pandas as pd

bowden = pd.read_excel(r"E:\disbr007\umn\ms_proj\thermokarst_locations_db\bowden_2008.xls")
lat_col = 'Latitude (dd.dddd)'
lon_col = 'Longitude (ddd.dddd)'
for col in [lat_col, lon_col]:
    bowden[col] = bowden[col].str[:-1]

bowden[lon_col] = bowden[lon_col].apply(lambda x: '-{}'.format(x))

bowden.to_csv(r"E:\disbr007\umn\ms_proj\thermokarst_locations_db\bowden_2008.csv")