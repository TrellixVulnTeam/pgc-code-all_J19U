# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:52:02 2020

@author: disbr007
"""
import argparse
import os
import matplotlib.pyplot as plt

import pandas as pd
import geopandas as gpd

from selection_utils.query_danco import query_footprint, list_danco_db, footprint_fields, count_table, pgc_ids
from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import onhand_ids, ordered_ids
from archive_analysis.calculate_density import calculate_density


logger = create_logger(__name__, 'sh', 'DEBUG')

out_txt = None
max_date = '2020-05-03'
plot = True
#%%
def check_where(where, op='AND'):
        """Checks if the input string exists already,
           if so formats correctly for adding to SQL"""
        if where:
            where += ' {} '.format(op)
        return where

# Inputs
# max_date = '2020-05-01'

# def missing_polar_stereo_ids(out_txt=None, max_date=None, plot=False):
    # Params
dg_stereo = 'dg_imagery_index_stereo_with_earthdem_region'
catalogid = 'catalogid'
chunksize = 100_000
where = 'cloudcover <= 50'
id_ordered = 'id_ordered'

# Get all onhand IDs
logger.info('Loading PGC IDs onhand...')
pgc_ids_oh = pgc_ids()
logger.info('PGC IDs onhand: {:,}'.format(len(pgc_ids_oh)))

# Get ordered IDs
logger.info('Loading IDs in order sheets...')
ordered = list(ordered_ids())
logger.info('IDs in order sheets: {:,}'.format(len(ordered)))

# Iterate over DG stereo
if max_date:
    where = check_where(where)
    where += """acqdate <= '{}'""".format(max_date)

columns = ['catalogid', 'acqdate', 'stereopair', 'cloudcover', 'platform','x1', 'y1', 'project']
table_total = count_table(dg_stereo, where=where)
logger.info('DG stereo IDs meeting criteria: {:,}'.format(table_total))
logger.debug('SQL criteria: {}'.format(where))
#%%
offset = 0
noh = gpd.GeoDataFrame()
while offset < table_total:
    logger.info('Loading chunk: {:,} - {:,}'.format(offset, chunksize+offset))
    chunk = query_footprint(dg_stereo, columns=columns,
                            where=where, limit=chunksize, offset=offset,
                            dryrun=False)
    # Check for missing IDs
    # Reduce to all stereo not on hand
    logger.debug('Identifying IDs not on hand...')
    noh_chunk = chunk[~chunk[catalogid].isin(pgc_ids_oh)]
    # Identify if polar
    logger.debug('Identifying polar IDs...')
    noh_poles = noh_chunk[noh_chunk['project'].isin(['ArcticDEM', 'REMA'])]
    logger.debug('Missing polar IDs from chunk: {:,}'.format(len(noh_poles)))

    noh = pd.concat([noh, noh_poles])
    
    # Increase offset
    offset += chunksize
    
logger.info('Missing polar IDs, with passed parameters: {:,}'.format(len(noh)))

noh[id_ordered] = noh[catalogid].isin(ordered)
logger.info('Missing polar IDs that were ordered: {:,}'.format(len(noh[noh[id_ordered]==True])))

if out_txt:
    with open(out_txt, 'w') as src:
        for mid in list(noh[catalogid]):
            src.write(mid)
            src.write('\n')
    logger.info('Missing IDs written to: {}'.format(out_txt))

#%% Summarize by EarthDEM region
countries = gpd.read_file(r'E:\disbr007\general\Countries_WGS84\Countries_WGS84.shp')
regions = query_footprint('pgc_earthdem_regions')
density = calculate_density(regions, noh)
density.dropna(subset=['count'], inplace=True)
#%% Plotting
if plot:
    from misc_utils.dataframe_plotting import plot_cloudcover, plot_timeseries_stacked
    
    plt.style.use('spyder4')
    fig, axes = plt.subplots(2, 2)
    axes = axes.flatten()
    
    plot_timeseries_stacked(noh, 'acqdate', catalogid, 'project', 'M', area=True, ax=axes[0])
    plot_timeseries_stacked(noh, 'acqdate', catalogid, id_ordered, 'M', area=True, ax=axes[2])
    plot_timeseries_stacked(noh, 'acqdate', catalogid, 'platform', 'M', area=True, ax=axes[3])
    plot_cloudcover(noh, 'cloudcover', ax=axes[1])
    
    plt.tight_layout()
    plt.show()
    density.hist(column='count')
    # maps
    plt.style.use('spy4_blank')
    fig_map, (ax_map1, ax_map2) = plt.subplots(2,1)
    countries.plot(color='none', edgecolor='white', linewidth=0.1, ax=ax_map1)
    density.plot(column='count', edgecolor='none', legend=True, 
                 cmap='Reds', alpha=0.5, ax=ax_map1)
    countries.plot(color='none', edgecolor='white', linewidth=0.1, ax=ax_map2)
    noh.plot(color='red', alpha=0.75, ax=ax_map2)
    plt.tight_layout()
    
 

#%%
regions = query_footprint('pgc_earthdem_regions')

#%%
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--out_txt', type=os.path.abspath,
                        help='Path to write text file of missing IDs')
    parser.add_argument('--max_date', type=str,
                        help='The most recent date to include, e.g. 2019-05-04')
    parser.add_argument('--plot', action='store_true',
                        help='Use this flag to plot missing IDs, by project over time and cloudcover.')
    
    args = parser.parse_args()
    
    missing_polar_stereo_ids(out_txt=args.out_txt,
                             max_date=args.max_date,
                             plot=args.plot)
