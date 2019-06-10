# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 09:10:58 2019

@author: disbr007
Creates a shapefile that is a refresh in the region selected from 
"""

import query_danco
import geopandas as gpd
import argparse, os
from imagery_order_sheet_maker_module import create_sheets
from id_parse_utils import date_words

def refresh_region_lut(refresh_region='polar_hma_above'):
    '''
    take in a refresh type and return relevent regions
    refresh_type: string, supported types ['polar_hma_above', 'nonpolar', 'global']
    '''
    supported_refreshes = ['polar_hma_above', 'nonpolar', 'global']
    if refresh_region in supported_refreshes:
        if refresh_region == 'polar_hma_above':
            regions = ['Antarctica', 'Arctic', 'ABoVE Polar', 'ABoVE Nonpolar', 'HMA']
        elif refresh_region == 'nonpolar':
            regions = ['Nonpolar']
        elif refresh_region == 'global':
            regions = ['Antarctica', 'Arctic', 'ABoVE Polar', 'HMA', 'Nonpolar', 'ABoVE Nonpolar', 'Nonpolar Ice']
    else:
        print('Refresh region unrecognized, supported refresh regions include {}'.format(supported_refreshes))
        regions = None
    return regions
    

def refresh(last_refresh, refresh_region, refresh_imagery):
    '''
    select ids for imagery order
    '''
    
    where = "acqdate >= '{}'".format(last_refresh)
    
    # Load regions shp
    regions_path = r"E:\disbr007\imagery_orders\all_regions.shp"
    regions = gpd.read_file(regions_path, driver='ESRI_Shapefile')
    
    # Load not on hand footprint -> since last refresh
    supported_refresh_imagery = ['mono_stereo', 'mono', 'stereo']
    if refresh_imagery in supported_refresh_imagery:
        if refresh_imagery == 'mono_stereo':
            noh_recent = query_danco.query_footprint('dg_imagery_index_all_notonhand_cc20', where=where)
        if refresh_imagery == 'mono':
            pass # Update this -> catalogid not in stereopair field anywhere, and stereopair == NONE
        if refresh_imagery == 'stereo':
            noh_recent = query_danco.stereo_noh(where=where)
    else:
        print('Refresh imagery type unrecognized, supported refresh imagery options include: {}'.format(supported_refresh_imagery))
   
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
    roi = refresh_region_lut(refresh_region)
    # Select region of interest
    noh_recent_roi = noh_recent[noh_recent.loc_name.isin(roi)]
    return noh_recent_roi


def project_dir(out_path, refresh_region):
    # Directory to write shp and order to
    date_in_words = date_words()
    dir_name = r'PGC_order_{}_{}_refresh'.format(date_in_words, refresh_region)
    dir_path = os.path.join(out_path, dir_name)
    return dir_path, dir_name
    

def write_selection(df, last_refresh, refresh_region, out_path):
    if not os.path.isdir(out_path):
        os.mkdir(out_path)

    dir_name = os.path.basename(out_path)
    # Name of shapefile to write
    write_name = '{}.shp'.format(dir_name)
    
    # Location to write shapefile to
    shp_path = os.path.join(out_path, write_name)
    
    # Write the shapefile
    df.to_file(shp_path, driver='ESRI Shapefile')
    return shp_path


if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("last_refresh", type=str, 
                        help="Date of last refresh: yyyy-mm-dd")
    parser.add_argument("refresh_region", type=str, 
                        help="Type of refresh, supported types: 'polar_hma_above', 'nonpolar', 'global'")
    parser.add_argument("refresh_imagery", type=str, 
                        help="Type of imagery to refresh, supported types: 'mono_stereo', 'mono', 'stereo'")
    parser.add_argument("out_path", type=str, nargs='?', default=os.getcwd(),
                        help="Path to write sheets and selection shape to")
    args = parser.parse_args()
    last_refresh = args.last_refresh
    refresh_region = args.refresh_region
    refresh_imagery = args.refresh_imagery
    out_path = args.out_path
    
    # Do it
    selection = refresh(last_refresh=last_refresh, refresh_region=refresh_region, refresh_imagery=refresh_imagery)
    write_selection(selection, last_refresh=last_refresh, refresh_region=refresh_region, out_path=out_path)
    