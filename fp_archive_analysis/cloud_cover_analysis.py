# -*- coding: utf-8 -*-
"""
Created on Fri May 10 09:04:28 2019

@author: disbr007
Analysis of cloud cover distribution of DG archive and imagery not on hand at PGC
"""

import geopandas as gpd
from query_danco import query_footprint

dg_archive = query_footprint(layer='index_dg', where="cloudcover < 50", table=True)

dg_archive.hist(column='cloudcover', bins=[0, 10, 20, 30, 40, 50])