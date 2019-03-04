# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 16:04:59 2019

@author: disbr007
"""

import geopandas as gpd
from query_danco import stereo_noh

if __name__ == '__main__':
    stereo_noh = stereo_noh()
    out_path = r'C:\Users\disbr007\imagery_orders\stereo_notonhand_cc20.shp'
    stereo_noh.to_file(driver='ESRI Shapefile', filename=out_path)