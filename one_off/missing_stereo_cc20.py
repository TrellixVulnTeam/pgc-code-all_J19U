# -*- coding: utf-8 -*-
"""
Created on Thu May 16 10:17:28 2019

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import fiona
import copy
import sys
import matplotlib.pyplot as plt
from query_danco import query_footprint

sys.path.insert(0,'C:\code\misc_utils')
from id_parse_utils import read_ids, write_ids


## Load data
missing_path = r"C:\temp\missing_cc20\missing_cc20.pkl" # all missing
missing = pd.read_pickle(missing_path)
platforms = list(missing.platform.unique())

# Archived ids in IMA: 85 ids
arc_path = r"C:\temp\missing_cc20\ids_archived_IMA.txt" # 85 missing IDs showing as archived
arc = read_ids(arc_path, sep=',')
# Not archived
narc = missing[~missing.catalogid.isin(arc)]


# Not in MFP
not_mfp_path = r'Z:\jeff\not_in_mfp_20190517\dg_896_942.shp'
not_mfp = gpd.read_file(not_mfp_path, driver='ESRI Shapefile')

# Adapt
adapt_path = r'E:\disbr007\pgc_index\nga_inventory20190219.gdb'
adapt = gpd.read_file(adapt_path, driver='OpenFileGDB', layer='nga_inventory20190219')



### Analyis
# Convert date column to datetime type
date_ready = copy.deepcopy(missing)
date_ready['acqdate'] = date_ready.acqdate.astype(str)
date_ready.acqdate = pd.to_datetime(date_ready.acqdate).dt.date
date_ready = date_ready.set_index('acqdate')
date_ready.index = pd.DatetimeIndex(date_ready.index)

# Determine stereo
min_cc = -1
max_cc = 20
where = "cloudcover > {} AND cloudcover <= {}".format(min_cc, max_cc)
all_stereo = query_footprint(layer='dg_imagery_index_stereo', where=where)
missing_stereo = date_ready[date_ready.catalogid.isin(all_stereo.catalogid)]

# By date (day)
by_date = date_ready.groupby(pd.Grouper(freq='D')).agg({'catalogid':'nunique'})
by_date.plot()

# By month
by_month = date_ready.groupby(pd.Grouper(freq='M')).agg({'catalogid': 'nunique'})
by_month.plot()
by_month.reset_index(inplace=True)
stereo_by_date = missing_stereo.groupby(pd.Grouper(freq='M')).agg({'catalogid':'nunique'})
stereo_by_date.plot()

# By platform and half year
by_half_year = date_ready.groupby([pd.Grouper(freq='6M'), 'platform']).agg({'catalogid':'nunique'})
by_half_year.unstack().plot(kind='bar', stacked=True)



