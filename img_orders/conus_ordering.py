#%% Imports
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 09:46:17 2020

@author: disbr007
"""
import pandas as pd
import geopandas as gpd

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, AutoLocator
import matplotlib.ticker as plticker
import matplotlib.dates as mdates

from misc_utils.id_parse_utils import remove_onhand
from misc_utils.logging_utils import create_logger
from misc_utils.dataframe_utils import det_cc_cat
from misc_utils.dataframe_plotting import plot_timeseries_stacked
from selection_utils.query_danco import query_footprint

# Logging
logger = create_logger(__name__, 'sh', 'DEBUG')
# create_module_loggers('sh', 'INFO')

#%% Load Data
# Params
conus_shp = r'E:\disbr007\general\US_States\tl_2017_us_state.shp'
dg_fp = 'dg_imagery_index_all_12months'

# Load data
logger.info('Loading footprints...')
# Conus
conus = gpd.read_file(conus_shp)
# Drop Alaska
conus = conus[conus['NAME']!='Alaska']
# Get bounding box
xmin, ymin, xmax, ymax = list(conus.total_bounds)
# Adjust xmax as it overlaps the IDL
xmax = -55

# Params
cc_max = 50
acqdate_min = "2019-03-31"
acqdate_max = "2020-04-01"

# DG Archive
# SQL
coords_where = """(x1 < {} AND x1 > {} AND y1 < {} AND y1 > {})""".format(xmax+0.5, xmin-0.5, ymax-0.5, ymin+0.5)
cc_where = "(cloudcover <= {})".format(cc_max)
acqdate_where = "(acqdate > '{}' AND acqdate < '{}')".format(acqdate_min, acqdate_max)
where = "{} AND {} AND {}".format(cc_where, coords_where, acqdate_where)
# Load
dg = query_footprint(dg_fp, where=where)
logger.debug('Loaded footprint: {}'.format(len(dg)))

logger.info('Identifying footprints over AOI...')
if dg.crs != conus.crs:
    conus = conus.to_crs(dg.crs)
dg_conus = gpd.overlay(dg, conus)
logger.debug('IDs over AOI: {}'.format(len(dg_conus)))

# Remove onhand ids
logger.info('Removing onhand IDs...')
dg_conus = dg_conus[dg_conus['catalogid'].isin(remove_onhand(dg_conus['catalogid']))]
logger.debug('Not onhand IDs: {}'.format(len(dg_conus)))

#%% Analysis
# Determine cloudcover category
dg_conus['acqdate'] = pd.to_datetime(dg_conus['acqdate'])
dg_conus.set_index('acqdate', inplace=True)
dg_conus['cc_cat'] = dg_conus['cloudcover'].apply(lambda x: det_cc_cat(x))

plt.style.use('ggplot')

fig, ax = plt.subplots(1,1)
conus.plot(ax = ax, facecolor='grey', edgecolor='white', linewidth=0.5)
dg_conus.plot(ax = ax)

#%% Aggregate
# dg_agg, _ = plot_timeseries_stacked(dg_conus.reset_index(), 'acqdate', 'catalogid', 'cc_cat', 
                                    # freq='m', area=True)
dg_gb = dg_conus.groupby([pd.Grouper(freq='M'), 'cc_cat']).agg({'catalogid':'nunique'})

# Field names
date_col = 'acqdate'

# Drop days from index
dg_gb = dg_gb.reset_index(level=0)
dg_gb[date_col] = dg_gb[date_col].apply(lambda x: x.strftime('%Y-%m-01'))
dg_gb[date_col] = pd.to_datetime(dg_gb[date_col])
dg_gb.set_index(date_col, append=True, inplace=True)
dg_gb = dg_gb.reorder_levels([date_col, 'cc_cat']).sort_index()

# 
dg_gb = dg_gb.unstack('cc_cat')
dg_gb.columns = dg_gb.columns.droplevel()

# Remove NaNs
dg_gb.fillna(value=0, inplace=True)

# Create culmulative columns in reverse order working back from the latest date
for col in ['cc20', 'cc21-30', 'cc31-40', 'cc41-50']:
    dg_gb['{}_culm'.format(col)] = dg_gb.loc[::-1, col].cumsum()[::-1]

# dg_gb['cc20_culm'] = dg_gb['cc20'].cumsum()

#%% Plot
fig, ax1 = plt.subplots(1,1)
# ax1, ax2 = axes.flatten()

# Manual plotting
width = 20
# last_l = None

# Plot bars
ax1.bar(dg_gb.index, dg_gb['cc20'],    width=width, label='cc20', 
       edgecolor='white')
ax1.bar(dg_gb.index, dg_gb['cc21-30'], width=width, label='cc21-30', 
        edgecolor='white', 
        bottom=dg_gb['cc20'])
ax1.bar(dg_gb.index, dg_gb['cc31-40'], width=width, label='cc31-40',
        edgecolor='white',
        bottom=dg_gb['cc20']+dg_gb['cc21-30'])
ax1.bar(dg_gb.index, dg_gb['cc41-50'], width=width, label='cc41-50',
        edgecolor='white',
        bottom=dg_gb['cc20']+dg_gb['cc21-30']+dg_gb['cc31-40'])

# Plot culmulative
fig, ax2 = plt.subplots(1,1)
ax2.bar(dg_gb.index, dg_gb['cc20_culm'],    width=width, label='cc20', 
       edgecolor='white')

ax2.bar(dg_gb.index, dg_gb['cc21-30_culm'], width=width, label='cc21-30', 
        edgecolor='white', 
        bottom=dg_gb['cc20_culm'])

ax2.bar(dg_gb.index, dg_gb['cc31-40_culm'], width=width, label='cc31-40',
        edgecolor='white',
        bottom=dg_gb['cc20_culm']+dg_gb['cc21-30_culm'])

ax2.bar(dg_gb.index, dg_gb['cc41-50_culm'], width=width, label='cc41-50',
        edgecolor='white',
        bottom=dg_gb['cc20_culm']+dg_gb['cc21-30_culm']+dg_gb['cc31-40_culm'])


for ax in [ax1, ax2]:
    ax.xaxis_date()
    plt.setp(ax.xaxis.get_majorticklabels(), 'rotation', 90)
    plt.setp(ax.xaxis.get_minorticklabels(), 'rotation', 90)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.legend().get_frame().set_edgecolor('white')
    
    ax.get_yaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))


