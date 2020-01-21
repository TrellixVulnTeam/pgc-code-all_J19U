# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 09:09:59 2020

@author: disbr007
Locates the not-on-hand IDs over a country of interest.
"""

import os

import geopandas as gpd
import matplotlib.pyplot as plt

from query_danco import query_footprint
from logging_utils import create_logger
from danco_table_summary import summarize_danco_fp
from id_parse_utils import write_ids

# INPUTS
country_name = 'United States'

# logger = create_logger(os.path.basename(__file__), 'sh')
logger = create_logger('onhand_country.py', 'sh', 'DEBUG')

PRJ_DIR = r'E:\disbr007\imagery_archive_analysis\onhand_country'
OUT_SHP = os.path.join(PRJ_DIR, 'noh_{}.shp'.format(country_name.replace(' ', '_')))
ALL_COUNTRIES_P = r'E:\disbr007\general\Countries_WGS84\Countries_WGS84.shp'
NAME = 'CNTRY_NAME' # field in countries shapefile holding country names
ID_FP = 'index_dg'
OH_TBL = 'pgc_imagery_catalogids'
DANCO_CATALOGID = 'catalogid'
PGC_CATALOGID = 'catalog_id'
NASA_CATALOGID = 'CATALOG_ID'
LAT_FLD = 'y1'
LON_FLD = 'x1'

# Load country of interest
all_countries = gpd.read_file(ALL_COUNTRIES_P)
country = all_countries[all_countries[NAME]==country_name]
logger.info('Loaded country: {}'.format(country_name))

# Load IDs in the rough area of country
min_x, min_y, max_x, max_y = country.total_bounds
pad = 1
min_x = min_x - pad
min_y = min_y - pad
max_x = max_x + pad
max_y = max_y + pad
# Check that min_x and max_x don't wrap the 180 longitude line,
# which would result in massive loading of footprints
if abs(max_x - min_x) > 200:
    # Eastern hemisphere
    max_xs = list(country.bounds.maxx)
    max_x_gtr = [x for x in max_xs if x < 180 and x > 0]
    max_x_gtr.sort()
    max_x_gtr = max_x_gtr[-1]
    
    min_xs = list(country.bounds.minx)
    min_x_gtr = [x for x in min_xs if x < 180 and x > 0]
    min_x_gtr.sort()
    min_x_gtr = min_x_gtr[0]
    
    # Western hemisphere
    max_x_ls = [x for x in max_xs if x > -180 and x < 0]
    max_x_ls.sort()
    max_x_ls = max_x_ls[-1]
    
    min_x_ls = [x for x in min_xs if x > -180 and x < 0]
    min_x_ls.sort()
    min_x_ls = min_x_ls[0]
    
    # Eastern longitude where    
    where = """({0} > {1} AND {0} < {2})""".format(LON_FLD, min_x_gtr-pad, max_x_gtr+pad)
    # Western longitude where
    where += """ OR ({0} > {1} AND {0} < {2})""".format(LON_FLD, min_x_ls-pad, max_x_ls+pad)
    where = '({})'.format(where)
    # Latitude
    where += """ AND ({0} > {1} AND {0} < {2})""".format(LAT_FLD, min_y-pad, max_y+pad)
    
else:
    where = """{0} > {2} and 
           {1} > {3} and 
           {0} < {4} and 
           {1} < {5}""".format(LON_FLD, LAT_FLD,
                               min_x, min_y, 
                               max_x, max_y)
    
logger.debug('Using country bounds to load initial footprints...\n{}'.format(where))
all_fps = query_footprint(ID_FP, where=where)
logger.info('Loaded initial footprints: {}'.format(len(all_fps)))
all_fps.geometry = all_fps.geometry.centroid


# Do select by location for only footprints with centroid in country
logger.info('Selecting IDs by centroid within country...')
country_fps = gpd.sjoin(all_fps, country, how='inner')
country_ids = country_fps[DANCO_CATALOGID]


# # Get all onhand IDs
onhand_tbl = query_footprint(OH_TBL, table=True)
onhand_ids = onhand_tbl[PGC_CATALOGID]

# Get all NASA IDs
nasa_tbl = gpd.read_file(r'E:\disbr007\imagery_archive_analysis\nga_inventory\nga_inventory_us.shp')
nasa_ids = list(nasa_tbl[NASA_CATALOGID])

# # Find missing IDs in country
noh_ids = set(country_ids) - set(onhand_ids) - set(nasa_ids)
logger.info('IDs not on hand in {}: {}'.format(country_name, len(noh_ids)))

noh_fps = all_fps[all_fps[DANCO_CATALOGID].isin(noh_ids)]

write_ids(noh_ids, os.path.join(PRJ_DIR, 'noh_nasa_pgc_ids.txt'))

summarize_danco_fp(noh_fps)
