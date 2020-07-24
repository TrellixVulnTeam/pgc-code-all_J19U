# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 13:08:08 2020

@author: disbr007
TODO: Add SQL to not load IDs in xtrack if they are in pgc_imagery_catalogids, then remove any ordered IDs
"""
# Suppress geopandas crs FutureWarning
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import argparse
import collections
import os
import sys
import matplotlib.pyplot as plt

import pandas as pd
import geopandas as gpd
# from tqdm import tqdm

from misc_utils.utm_area_calc import area_calc
from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import write_ids, get_platform_code, onhand_ids
from misc_utils.gpd_utils import select_in_aoi
from selection_utils.query_danco import query_footprint, count_table
from selection_utils.danco_utils import create_cid_noh_where


# Turn off pandas warning
pd.options.mode.chained_assignment = None

# Params
# noh = True
xtrack_tbl = 'dg_imagery_index_xtrack_cc20'
chunk_size = 50_000
area_col = 'area_sqkm'
catid1_fld = 'catalogid1'
catid2_fld = 'catalogid2'
cid1_oh_fld = 'catalogid1_oh'
cid2_oh_fld = 'catalogid2_oh'
columns = ['catalogid1', 'catalogid2', 'region_name', 'pairname', 'acqdate1']
land_shp = r'E:\disbr007\imagery_orders\coastline_include_fix_geom_dis.shp'


logger = create_logger(__name__, 'sh', 'DEBUG')
# sublogger = create_logger('selection_utils.query_danco', 'sh', 'INFO')


def create_where(sensors=None, min_date=None, max_date=None, within_sensor=False, noh=True,
                 projects=None, region_names=None):
    """Create where clause"""
    where = ''
    if sensors:
        sensor_where = ''
        for sensor in sensors:
            if sensor_where:
                sensor_where += ' OR '
            sensor_where += """(catalogid1 LIKE '{0}%%' OR catalogid2 LIKE '{0}%%')""".format(get_platform_code(sensor))
        if where:
            where += " AND "
        where += '({})'.format(sensor_where)
    if min_date:
        if where:
            where += " AND "
        where += "(acqdate1 >= '{}')".format(min_date)
    if max_date:
        if where:
            where += " AND "
        where += "(acqdate1 <= '{}')".format(max_date)
    if within_sensor:
        if where:
            where += " AND "
        where += "(SUBSTRING(catalogid1, 1, 3) = SUBSTRING(catalogid2, 1, 3))"
    if projects:
        if where:
            where += " AND "
        where += "(project in ({}))".format(str(projects)[1:-1])
    if region_names:
        if where:
            where += " AND "
        where += "(region_name in ({}))".format(str(region_names)[1:-1])
    if noh:
        if where:
            where += " AND "
        where += create_cid_noh_where(['catalogid1', 'catalogid2'], xtrack_tbl)
    logger.debug('SQL where: {}'.format(where))

    return where


# def select_in_aoi(gdf, aoi, centroid=False):
#     # logger.info('Finding IDs in AOI...')
#     gdf_cols = list(gdf)
#
#     if aoi.crs != gdf.crs:
#         aoi = aoi.to_crs(gdf.crs)
#     if centroid:
#         poly_geom = gdf.geometry
#         gdf.geometry = gdf.geometry.centroid
#         op = 'within'
#     else:
#         op = 'intersects'
#
#     gdf = gpd.sjoin(gdf, aoi, how='inner', op=op)
#     if centroid:
#         gdf.geometry = poly_geom
#
#     gdf = gdf[gdf_cols]
#     # TODO: Confirm if this is needed, does an 'inner' sjoin leave duplicates?
#     gdf.drop_duplicates(subset='pairname')
#
#     return gdf


def main(args):
    # Parse args
    out_path = args.out_path
    num_ids = args.number_ids
    update_ordered = args.update_ordered
    use_land = args.do_not_use_land
    remove_oh = args.do_not_remove_oh
    sensors = args.sensors
    within_sensor = args.within_sensor
    min_date = args.min_date
    max_date = args.max_date
    aoi_path = args.aoi
    projects = args.projects
    region_names = args.region_names
    out_footprint = args.out_footprint

    # Check for existence of aoi and out_path directory
    if aoi_path:
        if not os.path.exists(aoi_path):
            logger.error('AOI path does not exist: {}'.aoi_path)
            sys.exit()
        aoi = gpd.read_file(aoi_path)
    if not os.path.exists(os.path.dirname(out_path)):
        logger.warning('Out directory does not exist, creating: {}'.format(os.path.dirname(out_path)))
        os.makedirs(os.path.dirname(out_path))
    if out_footprint:
        if not os.path.exists(os.path.dirname(out_footprint)):
            logger.warning('Out directory does not exist, creating: {}'.format(os.path.dirname(out_footprint)))
            os.makedirs(os.path.dirname(out_footprint))

    where = create_where(sensors=sensors, min_date=min_date, max_date=max_date,
                         within_sensor=within_sensor, noh=remove_oh,
                         projects=projects, region_names=region_names)

    logger.info('Getting size of table with query...')
    table_total = count_table(xtrack_tbl, where=where)
    logger.info('Total table size with query: {:,}'.format(table_total))

    if remove_oh:
        # Get all onhand and ordered ids
        logger.info('Loading all onhand and ordered IDs...')
        oh_ids = set(onhand_ids(update=update_ordered))
        logger.info('Onhand and ordered IDs loaded: {:,}'.format(len(oh_ids)))
    else:
        oh_ids = set()

    # Load land shapefile if necessary
    if use_land:
        land = gpd.read_file(land_shp)

    # %% Iterate
    # Iterate chunks of table, calculating area and adding id1, id2, area to dictionary
    all_ids = []
    master = gpd.GeoDataFrame()
    limit = chunk_size
    offset = 0
    while offset < table_total:
        # Load chunk
        logger.info('Loading chunk: {:,} - {:,}'.format(offset, offset+limit))
        chunk = query_footprint(xtrack_tbl, columns=columns,
                                # orderby=orderby, orderby_asc=False,
                                where=where, limit=limit, offset=offset,
                                dryrun=False)

        remaining_records = len(chunk)

        # Remove records where both IDs are onhand
        if remove_oh:
            logger.info('Dropping records where both IDs are on onhand...')
            chunk = chunk[~((chunk['catalogid1'].isin(oh_ids)) & (chunk['catalogid2'].isin(oh_ids)))]
            remaining_records = len(chunk)
            logger.info('Remaining records: {:,}'.format(remaining_records))
            if remaining_records == 0:
                continue

        # Find only IDs in AOI if provided
        if aoi_path:
            logger.info('Finding IDs in AOI...')
            chunk = select_in_aoi(chunk, aoi=aoi)
            remaining_records = len(chunk)
            logger.debug('Remaining records in AOI: {:,}'.format(remaining_records))
            if remaining_records == 0:
                continue

        if use_land:
            logger.info('Selecting IDs over land only...')
            chunk = select_in_aoi(chunk, aoi=land, centroid=True)

            remaining_records = len(chunk)
            logger.info('Remaining records over land: {:,}'.format(len(chunk)))
            if remaining_records == 0:
                continue
        # %% Calculate area for chunk
        logger.info('Calculating area...')
        chunk = area_calc(chunk, area_col=area_col)

        # Combine with master
        logger.info('Combining chunk with master...')
        master = pd.concat([master, chunk])

        # Increase offset
        offset += limit

    # Select n records with highest area
    master = master.sort_values(by=area_col)
    master[cid1_oh_fld] = master[catid1_fld].isin(oh_ids)
    master[cid2_oh_fld] = master[catid2_fld].isin(oh_ids)

    if remove_oh:
        noh_str = ' not_on_hand'
    else:
        noh_str = ''
    logger.info('Finding {:,} out of {:,} IDs{}, starting with largest area...'.format(num_ids, len(master), noh_str))

    out_ids = set()
    kept_rows = set()
    num_kept_ids = len(out_ids)
    for i, row in master.iterrows():
        cid1 = row[catid1_fld]
        cid2 = row[catid2_fld]
        if not row[cid1_oh_fld] and cid1 not in out_ids:
            out_ids.add(cid1)
            kept_rows.add(row.name)
        if not row[cid2_oh_fld] and cid2 not in out_ids:
            out_ids.add(cid2)
            kept_rows.add(row.name)
        num_kept_ids = len(out_ids)
        if num_kept_ids >= num_ids:
            logger.info('{:,} IDs not on hand located. {:,} sqkm minimum kept.'.format(num_kept_ids, row[area_col]))
            break

    if num_kept_ids < num_ids:
        logger.warning('Only {:,} IDs found. Minimum area kept: {}'.format(num_kept_ids, row[area_col]))

    # Select kept pairs (rows)
    kept_pairs = master[master.index.isin(kept_rows)]
    if out_footprint:
        logger.info('Writing footprint of pairs to: {}'.format(out_footprint))
        kept_pairs.to_file(out_footprint)

    #%% Write
    if not os.path.exists(os.path.dirname(out_path)):
        os.makedirs(os.path.dirname(out_path))
    logger.info('Writing {:,} IDs to: {}'.format(len(out_ids), out_path))
    write_ids(out_ids, out_path)
    # write_ids(kept_areas, out_areas)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--out_path', type=os.path.abspath, required=True,
                        help='Path to write list of IDs to.')
    parser.add_argument('-n', '--number_ids', type=int,
                        help='The number of output IDs desired.')
    parser.add_argument('--update_ordered', action='store_true',
                        help='Rescan directory of order sheets and update list of ordered IDs.')
    parser.add_argument('--do_not_use_land', action='store_false',
                        help='Do not select using land shapefile.')
    parser.add_argument('--do_not_remove_oh', action='store_false',
                        help='Do not remove onhand IDs.')
    parser.add_argument('--sensors', nargs='+', choices=['WV01', 'WV02', 'WV03', 'GE01'],
                        default=['WV01', 'WV02', 'WV03'],
                        help='Select only these sesnors.')
    parser.add_argument('--within_sensor', action='store_true',
                        help='Only select same-sensor pairs (WV01-WV01, WV02-WV02, etc. not WV01-WV02, etc.')
    parser.add_argument('--min_date', type=str,
                        help='Earliest date to include. E.g.: 2020-01-31')
    parser.add_argument('--max_date', type=str,
                        help='Latsest date to include. E.g.: 2020-04-21')
    parser.add_argument('--aoi', type=os.path.abspath,
                        help='Path to shapefile to select within.')
    parser.add_argument('--projects', nargs='*', choices=['REMA', 'ArcticDEM', 'EarthDEM'],
                        help='Projects to include.')
    parser.add_argument('--region_names', nargs='+',
                        help='Regions to include.')
    parser.add_argument('--out_footprint', type=os.path.abspath,
                        help='Write footprint of pair overlaps for those pairs where at least one ID is kept.')

    args = parser.parse_args()

    main(args)
