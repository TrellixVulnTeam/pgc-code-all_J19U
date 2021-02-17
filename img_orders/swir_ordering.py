import argparse
import os

import geopandas as gpd
import pandas as pd

from selection_utils.query_danco import count_table, query_footprint
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

# Args
include_regions = ['arctic', 'antarctic', 'conus', 'global']
out_ids = r'C:\temp\swir_ids_polar_conus_noh.txt'

# Constants
index_dg = 'index_dg'
swir_where = "catalogid LIKE '104A%%'"
pgc_oh = 'pgc_imagery_catalogids'
pgc_swir_where = "catalog_id LIKE '104A%%'"
edem_lyr = 'pgc_earthdem_regions'
region_id = 'region_id'
limit = 50000


def swir_ordering(include_regions, out_ids):
    # Load earth_dem regions and pull region_ids out for selected regions
    edem = query_footprint(edem_lyr)
    regions = {'arctic': list(edem[edem['project']=='ArcticDEM']['region_id']),
               'antarctic': list(edem[edem['project']=='REMA']['region_id']),
               'conus': ['earthdem_04_great_lakes', 'earthdem_03_conus'],
               'global': list(edem['region_id'])}
    selected_region_ids = list()
    for sr in include_regions:
        selected_region_ids.extend(regions[sr])
    selected_region_ids = set(selected_region_ids)

    # Get selected regions
    selected_regions = edem[edem[region_id].isin(selected_region_ids)]
    uu = gpd.GeoDataFrame(geometry=[selected_regions.unary_union], crs='epsg:4326')

    # Iterate through index_dg and pull out SWIR IDs, then select only those in regions of interest
    master_swir = gpd.GeoDataFrame()
    offset = 0
    num_processed = 0
    swir_archive_count = count_table(index_dg, where=swir_where)
    logger.debug('Size of table for {} with WHERE {}: {:,}'.format(index_dg, swir_where, swir_archive_count))
    while num_processed <= swir_archive_count:
        logger.info('Loading with OFFSET {:,} LIMIT {:,}'.format(offset, limit))
        logger.debug('WHERE {}'.format(swir_where))
        swir = query_footprint(index_dg, where=swir_where, limit=limit, offset=offset)
        swir.geometry = swir.geometry.centroid
        logger.debug('Loaded SWIR: {:,}'.format(len(swir)))
        # Select in regions
        selected_swir_chunk = gpd.sjoin(swir, uu, op='within')
        offset += limit
        num_processed = offset

        logger.debug('SWIR IDs in selected regions in chunk: {:,}'.format(len(selected_swir_chunk)))
        if len(selected_swir_chunk) != 0:
            master_swir = pd.concat([master_swir, selected_swir_chunk])

    logger.info('SWIR IDs in regions: {:,}'.format(len(master_swir)))

    # Remove on hand swir
    oh_swir = set(list(query_footprint(pgc_oh, where=pgc_swir_where, table=True)['catalog_id']))
    selected_swir_noh = set(list(master_swir['catalogid'])) - oh_swir
    logger.info('SWIR IDs in regions and not on hand: {:,}'.format(len(selected_swir_noh)))

    # Write selected SWIR IDs
    with open(out_ids, 'w') as src:
        logger.debug('Writing IDs to: {}'.format(out_ids))
        for swir_id in selected_swir_noh:
            src.write('{}\n'.format(swir_id))

    return selected_swir_noh


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-ir', '--include_regions', choices=include_regions, nargs="+",
                        help='Regions to select SWIR Imagery from.')
    parser.add_argument('-o', '--out_ids', type=os.path.abspath,
                        help='Path to write text file of IDs.')

    args = parser.parse_args()

    swir_ordering(include_regions=args.include_regions, out_ids=args.out_ids)
