# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 09:10:58 2019

@author: disbr007
Creates a shapefile that is a refresh in the region selected 
"""
import argparse
import datetime
import os

import geopandas as gpd

from selection_utils.query_danco import query_footprint, mono_noh, stereo_noh, generate_rough_aoi_where
from misc_utils.id_parse_utils import date_words, remove_onhand, onhand_ids
from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import select_in_aoi


logger = create_logger(__name__, 'sh', 'DEBUG')

# Params
loc_name_fld = 'project'


def refresh_region_lut(refresh_region='polar_hma_above'):
    '''
    Uses a refresh region shortname to return relevent region names in AOI shapefile.
    refresh_region: string, supported types ['polar_hma_above', 'nonpolar', 'global']
    '''
    logger.debug('Refresh region: {}'.format(refresh_region))
    supported_refreshes = ['polar_hma_above', 'nonpolar', 'global', 'polar']
    # TODO: Check refresh_region = nonpolar to make sure it covers everything (HMA etc.)
    if refresh_region not in supported_refreshes:
        logger.warning("""Refresh region unrecognized, supported refresh regions 
                          include: {}""".format(supported_refreshes))
        regions = None

    if refresh_region == 'polar_hma_above':
        # regions = ['Antarctica', 'Arctic', 'ABoVE Polar',
        #            'ABoVE Nonpolar', 'HMA']
        regions = ['ArcticDEM', 'REMA']
    elif refresh_region == 'nonpolar':
        # regions = ['Nonpolar', 'Nonpolar Ice']
        regions = ['EarthDEM']
    elif refresh_region == 'global':
        # regions = ['Antarctica', 'Arctic', 'ABoVE Polar', 'HMA',
        #            'Nonpolar', 'ABoVE Nonpolar', 'Nonpolar Ice']
        regions = ['ArcticDEM', 'EarthDEM', 'REMA']
    elif refresh_region == 'polar':
        # regions = ['Antarctica', 'Arctic', 'ABoVE Polar']
        regions = ['ArcticDEM', 'REMA']

    return regions


def refresh(last_refresh, refresh_region, refresh_imagery, max_cc, min_cc, sensors,
            aoi_path=None, use_land=True, refresh_thru=None, drop_onhand=True):
    '''
    Select ids for imagery order
    cloudcover: cloudcover <= arg
    '''
    if not refresh_thru:
        # Use today's date
        refresh_thru = datetime.datetime.now().strftime('%Y-%m-%d')
        
    where = "(acqdate >= '{}' AND acqdate <= '{}') AND (cloudcover >= {} AND cloudcover <= {})".format(last_refresh, 
                                                                                                      refresh_thru,
                                                                                                      min_cc, max_cc)
    if sensors:
        where += " AND (platform IN ({}))".format(str(sensors)[1:-1])

    if aoi_path:
        aoi_where = generate_rough_aoi_where(aoi_path=aoi_path, x_fld='x1', y_fld='y1', pad=20.0)
        where += " AND {}".format(aoi_where)

    logger.debug('where: {}'.format(where))
        
    # Load regions shp
    regions_path = r"E:\disbr007\imagery_orders\all_regions.shp"
    logger.debug('Regions path: {}'.format(regions_path))
    # regions = gpd.read_file(regions_path, driver='ESRI_Shapefile')
    regions = query_footprint('pgc_earthdem_regions')
    

    # Load not on hand footprint -> since last refresh
    logger.info('Performing initial selection...')
    supported_refresh_imagery = ['mono_stereo', 'mono', 'stereo']
    logger.debug('Refresh imagery: {}'.format(refresh_imagery))
    if refresh_imagery in supported_refresh_imagery:
        if refresh_imagery == 'mono_stereo':
            noh_recent = query_footprint('index_dg', where=where)
        if refresh_imagery == 'mono':
            noh_recent = mono_noh(where=where, noh=drop_onhand)
        if refresh_imagery == 'stereo':
            noh_recent = stereo_noh(where=where, noh=drop_onhand)
    else:
        logger.warning("""Refresh imagery type unrecognized, supported refresh imagery 
              options include: {}""".format(supported_refresh_imagery))

    logger.info('Initial IDs found: {:,}'.format(len(noh_recent)))
    # noh_recent = noh_recent.drop_duplicates(subset='catalogid')

    ### Spatial join to identify region
    logger.info('Identifying region of selected imagery...')
    # Save original columns
    noh_recent_cols = list(noh_recent)
    noh_recent_cols.append(loc_name_fld)
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
    logger.debug('Regions included: {}'.format(roi))
    # Select region of interest
    noh_recent_roi = noh_recent[noh_recent[loc_name_fld].isin(roi)]
    # # Return to original columns
    # noh_recent_roi = noh_recent_roi[noh_recent_cols]

    logger.info('IDs in region(s) of interest: {:,}'.format(len(noh_recent_roi)))
    
    # Select only those features that intersect land polygons
    if use_land:
        logger.info('Selecting only imagery within land inclusion shapefile...')
        land_shp = r'E:\disbr007\imagery_orders\coastline_include_fix_geom_dis.shp'
        land = gpd.read_file(land_shp)
        # Drop 'index' columns if they exists
        drop_cols = [x for x in list(noh_recent_roi) if 'index' in x]
        noh_recent_roi = noh_recent_roi.drop(columns=drop_cols)
        noh_recent_roi = gpd.sjoin(noh_recent_roi, land, how='left')
        noh_recent_roi = noh_recent_roi[noh_recent_cols]

        logger.info('IDs over land: {}'.format(len(noh_recent_roi)))

    if aoi_path:
        # Drop 'index' columns if they exists
        drop_cols = [x for x in list(noh_recent_roi) if 'index' in x]
        noh_recent_roi = noh_recent_roi.drop(columns=drop_cols)

        aoi = gpd.read_file(aoi_path)
        noh_recent_roi = select_in_aoi(noh_recent_roi, aoi)
        # noh_recent_roi = noh_recent_roi[noh_recent_cols]
        logger.info('IDs over AOI: {}'.format(len(noh_recent_roi)))

    return noh_recent_roi


def project_dir(out_path, refresh_region):
    # Directory to write shp and order to
    date_in_words = date_words()
    dir_name = r'PGC_order_{}_{}_refresh'.format(date_in_words, refresh_region)
    dir_path = os.path.join(out_path, dir_name)
    
    return dir_path, dir_name
    

def write_selection(df, out_path):

    # if not os.path.isdir(out_path):
    #     os.mkdir(out_path)

    # dir_name = os.path.basename(out_path)
    # # Name of shapefile to write
    # write_name = '{}.shp'.format(dir_name)
    # # Location to write shapefile to
    # shp_path = os.path.join(out_path, write_name)
    # Write the shapefile
    shp_path = out_path
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
    parser.add_argument("out_path", type=os.path.abspath, default=os.getcwd(),
                        help="Path to write sheets and footprint selection shape to.")
    parser.add_argument("-rt", "--refresh_thru", type=str,
                        help='Last date to include in refresh. Inclusive. yyyy-mm-dd')
    parser.add_argument("--max_cc", type=int, default=20,
                        help='Cloudcover to select less than or equal to. Default = 20.')
    parser.add_argument("--min_cc", type=int, default=0,
                        help='Cloudcover to select greater than or equal to. Default = 0.')
    parser.add_argument("--sensors", nargs="+", default=['GE01', 'QB02', 'WV01', 'WV02', 'WV03'],
                        help='Sensors to select, default is all sensors. E.g. WV01 WV02')
    parser.add_argument("--drop_onhand", action='store_true',
                        help='Remove ids that have been ordered or are in the master footprint.')
    parser.add_argument("--aoi", type=os.path.abspath,
                        help='Path to AOI to subset selection.')
    parser.add_argument("--use_land", action='store_true',
                        help="Use coastline inclusion shapefile.")
    parser.add_argument("--dryrun", action='store_true',
                        help='Make selection and print statistics, but do not write anything.')
    parser.add_argument('--logfile', type=os.path.abspath,
                        help='Location to write logfile to.')


    args = parser.parse_args()

    last_refresh = args.last_refresh
    refresh_region = args.refresh_region
    refresh_imagery = args.refresh_imagery
    out_path = args.out_path
    refresh_thru = args.refresh_thru
    max_cc = args.max_cc
    min_cc = args.min_cc
    sensors = args.sensors
    aoi_path = args.aoi
    drop_onhand = args.drop_onhand
    use_land = args.use_land
    dryrun = args.dryrun
    logfile = args.logfile

    if not logfile:
        logfile = os.path.join(os.getcwd(), '{}.log'.format(os.path.basename(os.getcwd())))
    print('Creating logfile at: {}'.format(logfile))
    logger = create_logger(__name__, 'fh', 'DEBUG', filename=logfile)

    # Do it
    selection = refresh(last_refresh=last_refresh, 
                        refresh_region=refresh_region, 
                        refresh_imagery=refresh_imagery, 
                        refresh_thru=refresh_thru,
                        max_cc=max_cc,
                        min_cc=min_cc,
                        sensors=sensors,
                        use_land=use_land,
                        aoi_path=aoi_path,
                        drop_onhand=drop_onhand)
    
    if drop_onhand:
        oh_ids = onhand_ids()
        # not_onhand_ids = remove_onhand(selection['catalogid'])
        selection = selection[~selection['catalogid'].isin(oh_ids)]

    # Stats for printing to command line
    logger.info('IDs found: {:,}'.format(len(selection)))
    agg = {'catalogid': 'count',
           'acqdate': ['min', 'max'],
           'cloudcover': ['min', 'max'],
           'y1': ['min', 'max'],
           'sqkm_utm': 'sum'}

    selection_summary = selection.groupby('platform').agg(agg)
    logger.info('Summary:\n{}\n'.format(selection_summary))

    if not dryrun:
        write_selection(selection, out_path=out_path)
