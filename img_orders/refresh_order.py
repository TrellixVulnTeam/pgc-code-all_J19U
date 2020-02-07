# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 09:10:58 2019

@author: disbr007
Creates a shapefile that is a refresh in the region selected 
"""

import logging
# import pandas_profiling
import geopandas as gpd
import argparse, os

from selection_utils.query_danco import query_footprint, mono_noh, stereo_noh
from img_orders.img_order_sheets import create_sheets
from id_parse_utils import date_words, remove_onhand


#### Logging setup
# create logger
logger = logging.getLogger('polar_hma_above_refresh')
logger.setLevel(logging.INFO)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def refresh_region_lut(refresh_region='polar_hma_above'):
    '''
    Uses a refresh region shortname to return relevent region names in AOI shapefile.
    refresh_region: string, supported types ['polar_hma_above', 'nonpolar', 'global']
    '''
    supported_refreshes = ['polar_hma_above', 'nonpolar', 'global', 'polar']
    if refresh_region in supported_refreshes:
        if refresh_region == 'polar_hma_above':
            regions = ['Antarctica', 'Arctic', 'ABoVE Polar', 
                       'ABoVE Nonpolar', 'HMA']
        elif refresh_region == 'nonpolar':
            regions = ['Nonpolar', 'Nonpolar Ice']
        elif refresh_region == 'global':
            regions = ['Antarctica', 'Arctic', 'ABoVE Polar', 'HMA', 
                       'Nonpolar', 'ABoVE Nonpolar', 'Nonpolar Ice']
        elif refresh_region == 'polar':
            regions = ['Antarctica', 'Arctic', 'ABoVE Polar']
    else:
        logger.warning("""Refresh region unrecognized, supported refresh regions 
                          include: {}""".format(supported_refreshes))
        regions = None
    return regions


def refresh(last_refresh, refresh_region, refresh_imagery, max_cc, min_cc, sensors):
    '''
    Select ids for imagery order
    cloudcover: cloudcover <= arg
    '''
    
    where = "(acqdate > '{}') AND (cloudcover >= {} AND cloudcover <= {})".format(last_refresh, min_cc, max_cc)
    if sensors:
        where += " AND (platform IN ({}))".format(str(sensors)[1:-1])
    logger.debug('where: {}'.format(where))
        
    # Load regions shp
    regions_path = r"E:\disbr007\imagery_orders\all_regions.shp"
    logger.debug('Regions path: {}'.format(regions_path))
    regions = gpd.read_file(regions_path, driver='ESRI_Shapefile')
    

    # Load not on hand footprint -> since last refresh
    logger.info('Performing initial selection...')
    supported_refresh_imagery = ['mono_stereo', 'mono', 'stereo']
    if refresh_imagery in supported_refresh_imagery:
        if refresh_imagery == 'mono_stereo':
            noh_recent = query_footprint('index_dg', where=where)
        if refresh_imagery == 'mono':
            noh_recent = mono_noh(where=where)
        if refresh_imagery == 'stereo':
            noh_recent = stereo_noh(where=where)
    else:
        logger.warning("""Refresh imagery type unrecognized, supported refresh imagery 
              options include: {}""".format(supported_refresh_imagery))
   
    
    ### Spatial join to identify region
    logger.info('Identifying region of selected imagery...')
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
    

def write_selection(df, out_path):
    
    if not os.path.isdir(out_path):
        os.mkdir(out_path)

    dir_name = os.path.basename(out_path)
    # Name of shapefile to write
    write_name = '{}.shp'.format(dir_name)
    # Location to write shapefile to
    shp_path = os.path.join(out_path, write_name)
    # Write the shapefile
    logger.info('Writing selection to {}'.format(shp_path))
    df.to_file(shp_path, driver='ESRI Shapefile')

    return shp_path


if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("last_refresh", type=str, 
                        help="Date of last refresh: yyyy-mm-dd")
    parser.add_argument("refresh_region", type=str, 
                        help="""Type of refresh, supported types: 
                            'polar_hma_above', 'nonpolar', 'global', 'polar'""")
    parser.add_argument("refresh_imagery", type=str, 
                        help="""Type of imagery to refresh, supported types: 
                            'mono_stereo', 'mono', 'stereo'""")
    parser.add_argument("out_path", type=str, nargs='?', default=os.getcwd(),
                        help="Path to write sheets and footprint selection shape to.")
    parser.add_argument("--max_cc", type=int, default=20,
                        help='Cloudcover to select less than or equal to. Default = 20.')
    parser.add_argument("--min_cc", type=int, default=0,
                        help='Cloudcover to select greater than or equal to. Default = 0.')
    parser.add_argument("--sensors", nargs="+", default=['GE01', 'QB02', 'WV01', 'WV02', 'WV03'],
                        help='Sensors to select, default is all sensors. E.g. WV01 WV02')
    parser.add_argument("--drop_onhand", action='store_true',
                        help='Remove ids that have been ordered or are in the master footprint.')
    parser.add_argument("--dryrun", action='store_true',
                        help='Make selection and print statistics, but do not write anything.')

    args = parser.parse_args()
    last_refresh = args.last_refresh
    refresh_region = args.refresh_region
    refresh_imagery = args.refresh_imagery
    out_path = args.out_path
    max_cc = args.max_cc
    min_cc = args.min_cc
    sensors = args.sensors
    drop_onhand = args.drop_onhand
    dryrun = args.dryrun

    # Do it
    selection = refresh(last_refresh=last_refresh, 
                        refresh_region=refresh_region, 
                        refresh_imagery=refresh_imagery, 
                        max_cc=max_cc,
                        min_cc=min_cc,
                        sensors=sensors)
    
    if drop_onhand:
        not_onhand_ids = remove_onhand(selection['catalogid'])
        selection = selection[selection['catalogid'].isin(not_onhand_ids)]
    
    # Stats for printing to command line
    logger.info('IDs found: {}'.format(len(selection)))
    agg = {'catalogid':'count', 'acqdate':['min', 'max'], 'cloudcover':['min', 'max'], 'y1':['min', 'max']}
    selection_summary = selection.groupby('platform').agg(agg)
    logger.info('Summary:\n{}\n'.format(selection_summary))

    
    if not dryrun:
        write_selection(selection, out_path=out_path)
        