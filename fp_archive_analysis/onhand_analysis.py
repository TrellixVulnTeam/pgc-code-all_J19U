# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 11:02:16 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator
from functools import reduce

import os, calendar, datetime, sys, logging, collections, tqdm

from query_danco import query_footprint
from id_parse_utils import read_ids


def range_tuples(start, stop, step):
    
    ranges = []
    lr = range(start, stop+step, step)
    for i, r in enumerate(lr):
        if i < len(lr)-1:
            ranges.append((r, lr[i+1]))
    return ranges


def y_fmt(y, pos):
    '''
    Formatter for y axis of plots. Returns the number with appropriate suffix
    y: value
    pos: *Not needed?
    '''
    decades = [1e9, 1e6, 1e3, 1e0, 1e-3, 1e-6, 1e-9 ]
    suffix  = ["G", "M", "k", "" , "m" , "u", "n"  ]
    if y == 0:
        return str(0)
    for i, d in enumerate(decades):
        if np.abs(y) >=d:
            val = y/float(d)
            signf = len(str(val).split(".")[1])
            if signf == 0:
                return '{val:d} {suffix}'.format(val=int(val), suffix=suffix[i])
            else:
                if signf == 1:
                    if str(val).split(".")[1] == "0":
                       return '{val:d}{suffix}'.format(val=int(round(val)), suffix=suffix[i]) 
                tx = "{"+"val:.{signf}f".format(signf = signf) +"} {suffix}"
                return tx.format(val=val, suffix=suffix[i])
    return y


## Set up logging
logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)



#### Load DG archives
data_path = r'E:\disbr007\imagery_archive_analysis\onhand_analysis\data'



## Intrack - pull out stereopair ids and stack them with catalogid
logging.info('Loading intrack data...')
it1 = query_footprint('dg_imagery_index_stereo', 
                     columns=['catalogid', 'cloudcover', 'acqdate'], 
                     where="""cloudcover <= 50""")

it2 = query_footprint('dg_imagery_index_stereo', 
                     columns=['stereopair', 'cloudcover', 'acqdate'], 
                     where="""cloudcover <= 50""")

logger.info('Processing intrack...')
it2.rename({'stereopair': 'catalogid'}, inplace=True)
it = pd.concat([it1, it2])
del it1, it2

# cc20 and cc20-50
it20 = it[it['cloudcover'] <= 20]
it50 = it[(it['cloudcover'] > 20)]

# Get all stereo ids for removing from archive to determine mono ids
it_ids = set(list(it['catalogid']))


#### Xtrack
logger.info('Loading cross track...')
xt_all = query_footprint('dg_imagery_index_xtrack_cc20',
                     columns=['catalogid1', 'acqdate1', 'catalogid2', 'acqdate2'])

logger.info('Processing cross track...')
xt1 = xt_all[['catalogid1', 'acqdate1']]
xt1.drop_duplicates(subset='catalogid1', inplace=True)
xt2 = xt_all[['catalogid2', 'acqdate2']]
xt2.drop_duplicates(subset='catalogid2', inplace=True)

## Rename columns to match and concat
ren = {'catalogid1': 'catalogid', 'catalogid2': 'catalogid',
       'acqdate1': 'acqdate','acqdate2': 'acqdate'}
xt1.rename(ren, axis='columns', inplace=True)
xt2.rename(ren, axis='columns', inplace=True)

xt = pd.concat([xt1, xt2])
xt.drop_duplicates(subset='catalogid', inplace=True)
del xt1, xt2, xt_all


## Mono - remove stereo from all cc20
logger.info('Determining mono...')
mono20 = query_footprint('dg_imagery_index_all_cc20',
                       columns=['catalogid', 'acqdate'])
mono20 = mono20[~mono20['catalogid'].isin(it_ids)]


## Archive - exported from ArcMap as text file of catalogid, acqdate, cloudcover
#dg_archive = pd.read_csv(r'E:\disbr007\imagery_archive_analysis\onhand_analysis\data\index_dg.txt',
#                         parse_dates=[1])
logger.info('Loading DG archive...')
dg_archive = query_footprint('index_dg', columns=['catalogid', 'cloudcover', 'acqdate'])
dg_archive['acqdate'] = pd.to_datetime(dg_archive['acqdate'])
dg_archcc20 = dg_archive[dg_archive['cloudcover'] <= 20]
dg_archcc50 = dg_archive[dg_archive['cloudcover'] <= 50]

## Create dict of all dfs to plot
dfs = {'DG_Archive': {'base': dg_archive},
       'DG_cc20': {'base': dg_archcc20},
       'DG_cc50': {'base': dg_archcc50},
       'Intrack_cc20': {'base': it20},
       'Intrack_cc50': {'base': it50},
       'Cross_Track': {'base': xt},
       'Mono': {'base': mono20}}

logger.info('Determining on hand...')
#### Load PGC / NASA and Determine On Hand
## PGC
pgc_id_p = r'C:\pgc_index\catalog_ids.txt'
pgc_ids = read_ids(pgc_id_p)
## NASA
nasa_id_p = r'C:\pgc_index\adapt_ids.txt'
nasa_ids = read_ids(nasa_id_p)


## Loop columns, determining onhand status and aggregating by month and onhand status
for name, sub_dict in dfs.items():
    df = sub_dict['base']
    df['onhand'] = 'Not Onhand'
    df['onhand'] = np.where(df['catalogid'].isin(nasa_ids), 'NASA', df['onhand'])
    df['onhand'] = np.where(df['catalogid'].isin(pgc_ids), 'PGC', df['onhand'])
    
    # Convert date columns to datetime
    try:
        df['acqdate'] = pd.to_datetime(df['acqdate'])
        df.set_index('acqdate', inplace=True)
    except:
        pass
    
    # Aggregrate by month and onhand status
    agg = {'catalogid': 'count'}
    dfs[name]['agg'] = df.groupby([pd.Grouper(freq='M'),'onhand']).agg(agg)
    dfs[name]['agg'].rename(columns={'catalogid': 'Strips'}, inplace=True)


#### Create Totals DFs
for name, sub_dict in dfs.items():
    sub_dict['agg'] = sub_dict['agg'].unstack()
    cols = list(sub_dict['agg'])
    idx = sub_dict['agg'].index
    sub_dict['totals'] = pd.DataFrame(columns=cols, index=idx)
    sub_dict['agg']['Total'] = sub_dict['agg'].sum(axis=1)
    for col in cols:
        sub_dict['totals'][col] = sub_dict['agg'][col] / sub_dict['agg']['Total'] * 100


#### Write statistics to text file
stats_path = os.path.join(data_path, 'statistics.txt')
with open(stats_path, 'w') as stats:
    for name, sub_dict in dfs.items():
        total_ids = len(sub_dict['base'])
        
        n_pgc_ids = len(sub_dict['base'].loc[sub_dict['base']['onhand'] == 'PGC'])
        pgc_perc = (n_pgc_ids / total_ids) * 100
        
        n_nasa_ids = len(sub_dict['base'].loc[sub_dict['base']['onhand'] == 'NASA'])
        nasa_perc = (n_nasa_ids / total_ids) * 100
        
        n_not_oh_ids = len(sub_dict['base'].loc[sub_dict['base']['onhand'] == 'Not Onhand'])
        not_oh_perc = (n_not_oh_ids / total_ids) * 100
        
        stats.write('{}\n'.format(name.upper()))
        stats.write('Total IDs: {:,}\n'.format(total_ids))
        stats.write('PGC: {:,} ({:.0f}%)\n'.format(n_pgc_ids, pgc_perc))
        stats.write('NASA: {:,} ({:.0f}%)\n'.format(n_nasa_ids, nasa_perc))
        stats.write('Not OH: {:,} ({:.0f}%)\n'.format(n_not_oh_ids, not_oh_perc))
        stats.write('\n\n\n'.format(total_ids))


# Save out to pickles
for name, sub_dict in dfs.items():
    sub_dict['agg'].to_pickle(os.path.join(data_path, '{}_agg.pkl'.format(name)))
    sub_dict['base'].to_pickle(os.path.join(data_path, '{}_base.pkl'.format(name)))
    sub_dict['totals'].to_pickle(os.path.join(data_path, '{}_totals.pkl'.format(name)))


