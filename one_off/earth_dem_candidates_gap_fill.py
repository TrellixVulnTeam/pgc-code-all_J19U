# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 13:31:22 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import logging
from query_danco import query_footprint
from id_parse_utils import read_ids, write_ids
from ids_order_sources import id_order_loc_update


## Load selection shapfile (geocells)
logging.info('Loading geocells of interest.')
gc_p = r'E:\disbr007\imagery_orders\PGC_order_2019jul08_earthDEM_candidates\EarthDEM_candidates\EarthDEM_candidates.shp'
gc = gpd.read_file(gc_p, driver='ESRI Shapefile')


## Load danco footprint and do sjoin
fp_name = 'dg_imagery_index_stereo'

# Query danco
logging.info('Querying danco footprint.')
fp = query_footprint(fp_name, 
                     where='cloudcover >=0 and cloudcover <= 50', 
                     columns=['catalogid', 'stereopair', 'cloudcover', 'acqdate'])
# Do spatial join on intrack stereo cc20
sel = gpd.sjoin(fp, gc, how='inner')


### Load xtrack footprint and do sjoin
#fp = query_footprint('dg_imagery_index_xtrack_cc20',
#                     columns=['catalogid1', 'catalogid2'])
#sel_x = gpd.sjoin(fp, gc, how='inner')


## Get all ids out as one list
logging.info('Combining catalogid and stereopair into one list.')
ids = list(sel['catalogid']) + list(sel['stereopair'])# + list(sel_x['catalogid1']) + list(sel_x['catalogid2'])
ids = set(ids)

logging.info('Removing onhand IDs.')
pgc_ids = set(read_ids(r'C:\pgc_index\catalog_ids.txt'))
ordered_ids = set(list(id_order_loc_update()['ids']))
oh_ids = pgc_ids.union(ordered_ids)


ids_noh = ids - oh_ids

logging.info('Writing IDs text and shapefile.')
write_ids(ids_noh, out_path=r'E:\disbr007\imagery_orders\PGC_order_2019jul08_earthDEM_candidates\EarthDEM_candidates\ids_to_order.txt')

#sel_x.rename(columns={"catalogid1": "catalogid", "catalogid2": "stereopair"}, inplace=True)

#selection = pd.concat([sel, sel_x])
selection = sel
selection = selection[selection['catalogid'].isin(ids_noh) | selection['stereopair'].isin(ids_noh)]
selection.to_file(r'E:\disbr007\imagery_orders\PGC_order_2019jul08_earthDEM_candidates\EarthDEM_candidates\ids_to_order_cc0-50.shp', 
                  driver='ESRI Shapefile')