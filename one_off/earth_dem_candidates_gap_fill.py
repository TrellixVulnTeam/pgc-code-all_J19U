"""
Created on Mon Jul  8 13:31:22 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import logging, os
#from fp_selection_utils.query_danco import query_footprint
from query_danco import query_footprint
from id_parse_utils import read_ids, write_ids
from ids_order_sources import get_ordered_ids


proj_dir = r'E:\disbr007\imagery_orders\PGC_order_2019jul08_earthDEM_candidates\EarthDEM_candidates'

## Load selection shapfile (geocells)
logging.info('Loading geocells of interest.')
gc_p = os.path.join(proj_dir, 'EarthDEM_candidates.shp')
gc = gpd.read_file(gc_p, driver='ESRI Shapefile')


## Load danco footprint and do sjoin
fp_name = 'dg_imagery_index_stereo'


# Query danco
logging.info('Querying danco footprint.')
fp = query_footprint(fp_name, 
                     where='cloudcover >=0 and cloudcover <= 20', 
                     columns=['catalogid', 'stereopair', 'cloudcover', 'acqdate'])

sel = fp

# Do spatial join on intrack stereo to select only geocells of interest
#sel = gpd.sjoin(fp, gc, how='inner')
#sel.drop_duplicates(['catalogid','stereopair'], keep='first', inplace=True)


## Get all ids out as one list
logging.info('Combining catalogid and stereopair into one list.')
sel_ids = list(sel['catalogid']) + list(sel['stereopair'])
sel_ids = set(sel_ids)


## Remove onhand ids in either master footprint or any order sheet
logging.info('Removing onhand IDs.')
pgc_ids = set(read_ids(r'C:\pgc_index\catalog_ids.txt')) # mfp
ordered_ids = set(get_ordered_ids()) # ordered ids from sheets
oh_ids = pgc_ids.union(ordered_ids) 

ids_noh = sel_ids - oh_ids


## Write list of ids not on hand, i.e. ids to order, to a text file, including stereopair ids
logging.info('Writing IDs text and shapefile.')
write_ids(ids_noh, out_path=os.path.join(proj_dir, 'missing_global_cc20.txt'))


## Write shapefile, just for viewing
selection = sel
selection = selection[selection['catalogid'].isin(ids_noh) | selection['stereopair'].isin(ids_noh)]
selection.to_file(os.path.join(proj_dir, 'missing_global_cc20.shp'), driver='ESRI Shapefile')