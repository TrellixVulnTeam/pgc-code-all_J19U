# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 09:10:58 2019

@author: disbr007
"""

import query_danco
import geopandas as gpd
import argparse, os


def refresh_region_lut(refresh_type='polar_hma_above'):
    '''
    take in a refresh type and return relevent regions
    refresh_type: string, supported types ['polar_hma_above', 'nonpolar', 'global']
    '''
    supported_refreshes = ['polar_hma_above', 'nonpolar', 'global']
    if refresh_type in supported_refreshes:
        if refresh_type == 'polar_hma_above':
            regions = ['antarctica', 'arctic']
        elif refresh_type == 'nonpolar':
            regions = ['nonpolar']
        elif refresh_type == 'global':
            regions = ['antarctica', 'arctic', 'nonpolar']
    else:
        print('Refresh type unrecognized, supported refreshes include {}'.format(supported_refreshes))
        regions = None
    return regions
    

def refresh(last_refresh, roi):
    '''
    select ids for imagery order
    '''
    # Load regions shp
    regions_path = r"E:\disbr007\imagery_orders"
    regions = gpd.read_file(regions_path, driver='ESRI_Shapefile')
    
    # Load not on hand footprint -> since last refresh
    noh_recent = query_danco.query_footprint('dg_imagery_index_all_notonhand_cc20', where="acqdate > '{}'".format(last_refresh))
    
    ### Spatial join to identify region
    # Calculate centroid
    noh_recent['centroid'] = noh_recent.centroid
    noh_recent.set_geometry('centroid', inplace=True)
    # Locate region of centroid
    noh_recent = gpd.sjoin(noh_recent, regions, how='left', op='within')
    noh_recent.drop('centroid', axis=1, inplace=True)
    noh_recent.set_geometry('geom', inplace=True)
    
    ### Identify only those in the region of interest
    # Get regions of interest based on type of refresh
    roi = refresh_region_lut('polar_hma_above')
    # Select region of interest
    noh_recent_roi = noh_recent[noh_recent.region.isin(roi)]
    return noh_recent_roi

def write_selection(df, last_refresh, refresh_type, out_path):
    # Directory to write shp and order to
    write_dir = r'{}_{}'.format(last_refresh, refresh_type)
    if not os.path.isdir(write_dir):
        os.mkdir(write_dir)
    # Name of shapefile to write
    write_name = '{}.shp'.format(write_dir)
    # Location to write shapefile to
    write_path = os.path.join(r'E:\disbr007\imagery_orders', write_dir, write_name)
    # Write the shapefile
    df.to_file(write_path, driver='ESRI Shapefile')
    return write_path
    

# Specify date of last refresh and refresh type
last_refresh = '2019-02-20'
refresh_type = 'polar_hma_above'

roi = refresh_region_lut('polar_hma_above')
selection = refresh(last_refresh=last_refresh, roi=roi, out_path=write_path)




