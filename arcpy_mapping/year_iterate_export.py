# -*- coding: utf-8 -*-
"""
Created on Tue Oct  8 15:10:01 2019

@author: disbr007
"""

import arcpy
import os


mxd_p = r'E:\disbr007\imagery_orders\imagery_orders.mxd'
mxd = arcpy.mapping.MapDocument(mxd_p)

date_range = range(2007, 2019)

## Get dataframes
dfs = arcpy.mapping.ListDataFrames(mxd)

df = dfs[0]
## Get fp layer
fp = arcpy.mapping.ListLayers(mxd, df)