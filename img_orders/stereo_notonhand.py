 # -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 16:04:59 2019

@author: disbr007
Updates a local shapefile of stereo not on hand by combining danco layers:
    stereo_notonhand left_cc20
    stereo_notonhand_right_cc20
"""

import geopandas as gpd
from query_danco import stereo_noh

if __name__ == '__main__':
    out_path = r'C:\Users\disbr007\imagery_orders\stereo_notonhand_cc20.shp'
    print('Updating stereo not onhand shapefile at: {}'.format(out_path))
    stereo_noh = stereo_noh()
    stereo_noh.to_file(driver='ESRI Shapefile', filename=out_path)