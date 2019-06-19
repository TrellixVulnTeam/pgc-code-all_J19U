# -*- coding: utf-8 -*-
"""
Created on Thu May 16 10:17:28 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import fiona, copy, sys, tqdm
import matplotlib.pyplot as plt
from query_danco import query_footprint

sys.path.insert(0,'C:\code\misc_utils')
from id_parse_utils import read_ids, write_ids
from dataframe_utils import dbf2DF


## Load data
missing_path = r"C:\temp\missing_cc20\missing_cc20.pkl" # all missing
missing = pd.read_pickle(missing_path)
all_missing = copy.deepcopy(missing)
all_missing_ids = list(missing.catalogid)
platforms = list(missing.platform.unique())

## Archived ids in IMA: 85 ids
#arc_path = r"C:\temp\missing_cc20\ids_archived_IMA.txt" # 85 missing IDs showing as archived
#arc = read_ids(arc_path, sep=',')
## Not archived
#narc = missing[~missing.catalogid.isin(arc)]

## Adapt
adapt_path = r'E:\disbr007\pgc_index\nga_inventory20190219.dbf'
#adapt = gpd.read_file(adapt_path, driver='OpenFileGDB', layer='nga_inventory20190219')
adapt = dbf2DF(adapt_path, upper=False)
adapt_ids = list(adapt.CATALOG_ID.unique())
# Number of missing ids in adapt
missing_adapt = list(set(all_missing_ids) - (set(all_missing_ids) - set(adapt_ids)))
# Running total
missing_ids = list(set(all_missing_ids) - set(adapt_ids))
missing = missing[missing.catalogid.isin(missing_ids)]
print('Missing in ADAPT: {}'.format(len(missing_adapt)))
print('Missing after removing ADAPT: {}'.format(len(missing)))

# Not in MFP
not_mfp_path = r'Z:\jeff\not_in_mfp_20190517\dg_896_942.shp'
not_mfp = gpd.read_file(not_mfp_path, driver='ESRI Shapefile')
not_mfp_ids = list(not_mfp.CATALOG_ID.unique())
# Missing ids not in master footprint yet
missing_nmfp = list(set(all_missing_ids) - (set(all_missing_ids) - set(not_mfp_ids)))
# Running total
missing_ids = list(set(missing_ids) - set(not_mfp_ids))
missing = missing[missing.catalogid.isin(missing_ids)]
print('Missing not yet in MFP: {}'.format(len(missing_nmfp)))
print('Missing after removing NotMFP: {}'.format(len(missing)))

# IMA Ordered AS OF MARCH
#ima_ordered_path1_old = r'C:\temp\missing_cc20\ima_ordered1.csv'
#ima_ordered_path2_old = r'C:\temp\missing_cc20\ima_ordered2.csv'
#ima1_old = pd.read_csv(ima_ordered_path1_old, header=None, names=['catalogid'])
#ima2_old = pd.read_csv(ima_ordered_path2_old, header=None, names=['catalogid'])
#ima_old = pd.concat([ima1_old, ima2_old], sort=False)
#ima_old_ids = list(ima_old.catalogid.unique())
#missing_ima_old = list(set(all_missing_ids) - (set(all_missing_ids) - set(ima_old_ids)))
'''
ima_ordered_path1 = r'C:\temp\missing_cc20\ima_ordered1_may2019.csv'
ima_ordered_path2 = r'C:\temp\missing_cc20\ima_ordered2_may2019.csv'
ima1 = pd.read_csv(ima_ordered_path1, header=None, names=['catalogid'])
ima2 = pd.read_csv(ima_ordered_path2, header=None, names=['catalogid'])
ima = pd.concat([ima1, ima2], sort=False)
ima_ids = list(ima.catalogid.unique())
# Missing ids that are in IMA
missing_ima = list(set(all_missing_ids) - (set(all_missing_ids) - set(ima_ids)))
missing_in_ima = all_missing[all_missing.catalogid.isin(ima_ids)]
# Running total
missing_ids = list(set(missing_ids) - set(ima_ids))

print('Missing in IMA: {}'.format(len(missing_ima)))
print('Missing after removing IMA: {}'.format(len(missing_ids)))
print('Remaining missing: {}'.format(len(missing)))
'''
'''
### UNKNOWN
def region_loc(y1):
    # Determine region based on y coordinate
    if y1 >= -90.0 and y1 < -60.0:
        region = 'Antarctic'
    elif y1 <= 90.0 and y1 > 60.0:
        region = 'Arctic'
    elif y1 >= -60.0 and y1 < 60.0:
        region = 'Nonpolar'
    return region

missing['region'] = missing.y1.apply(region_loc)
missing.plot()
#missing_recent = missing[(missing.catalogid.isin(ima_ids) missing.acqdate>'2018-10-01']
#missing_recent.plot()


### Analyis
# Convert date column to datetime type
date_ready = copy.deepcopy(missing)
date_ready['acqdate'] = date_ready.acqdate.astype(str)
date_ready.acqdate = pd.to_datetime(date_ready.acqdate).dt.date
date_ready = date_ready.set_index('acqdate')
date_ready.index = pd.DatetimeIndex(date_ready.index)

# By date (day)
by_date = date_ready.groupby(pd.Grouper(freq='D')).agg({'catalogid':'nunique'})
by_date.plot()

# By month
by_month = date_ready.groupby(pd.Grouper(freq='M')).agg({'catalogid': 'nunique'})
by_month.plot()
by_month.reset_index(inplace=True)

# By platform and half year
by_half_year = date_ready.groupby([pd.Grouper(freq='6M'), 'platform']).agg({'catalogid':'nunique'})
by_half_year.unstack().plot(kind='bar', stacked=True)
'''