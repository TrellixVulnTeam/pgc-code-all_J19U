# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 14:44:39 2020

@author: disbr007
"""

import geopandas as gpd
from osgeo import ogr

from valid_data import valid_data
from clip2shp_bounds import warp_rasters

# Path to selection footprint
selection_path = r'E:\disbr007\UserServicesRequests\Projects\kbollen\master_dem_selection.shp'
selection = gpd.read_file(selection_path)

# Path to shapefile of polygon AOIs
aoi_path = r'E:\disbr007\UserServicesRequests\Projects\kbollen\TerminusBoxes\GreenlandPeriph_BoxesUpdated_4326.shp'
aoi = gpd.read_file(aoi_path)

for bid in aoi.BoxID.unique():
    # AOI for current BoxID
    aoi_bid = aoi[aoi.BoxID==bid]    
    
    # Selection for the current BoxID
    s_bid = selection[selection.BoxID==bid]
    # SUBSET for testing
    s_bid = s_bid[:3]
    rasters = list(s_bid.win_path)
    
    # Copy current AOI to memory OGR layer 
    src_ds = ogr.Open(aoi_bid.to_json())
    mem_driver = ogr.GetDriverByName('Memory')
    mem_ds = mem_driver.CreateDataSource('out')
    mem_layer = mem_ds.CopyLayer(src_ds.GetLayer(), 'mem_layer')
    
    # warp_rasters(mem_layer, rasters, out_dir)
    break
    

# selection['valid_data'] = None

