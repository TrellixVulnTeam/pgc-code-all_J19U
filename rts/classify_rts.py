# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
# import operator

import pandas as pd
# from pandas.api.types import is_numeric_dtype
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from obia_utils.neighbors import subset_df, adj_neighbor

pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'DEBUG')

#%%
from datetime import datetime
start = datetime.now()

logger.debug('Reading in segmentation...')
# seg_path = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_tpi31_tpi81_tpi101_stk_a6g_sr5_rr0x35_ms100_tx500_ty500_stats_wbt.shp'
seg_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500_stats_nbs_wbt.shp'
seg = gpd.read_file(seg_path)
# Existing columns
unique_id = 'label'
# tpi31_mean = 'tpi31_mean'
# slope_mean = 'slope_mean'
# Remove extra columns for testing
# seg = seg[[unique_id, tpi31_mean, slope_mean, 'geometry']]

# Set index
seg.set_index(unique_id, inplace=True)
logger.debug('DataFrame has unique index: {}'.format(str(seg.index.is_unique)))

#%% Determine headwalls
# ID Steep
seg['steep'] = seg['slope_mean'] > 10

#%% Params

hw_params = [('slope_mean',  '>', 6.5)]

hw = subset_df(seg, params=hw_params)

# Plot
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
# from matplotlib.transforms import Bbox

vc = 'MDEC_media'
plt.style.use('spy4_blank')
fig, ax = plt.subplots(1,1)

# ax.axis('off')
# ax.tick_params(axis='both', reset=True)
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="3%", pad=0.2)

# seg.plot(ax=ax, column=vc, edgecolor='white', linewidth=0.75, linestyle=':', 
        # legend=True, cax=cax,
        # vmin=0, vmax=0.3)
hw.plot(ax=ax, column='steep', edgecolor='black', linewidth=0.25)

# ax.axis([-1752000, -1751600, -559300, -558910])
for spine in ['bottom', 'top', 'left', 'right']:
    ax.spines[spine].set_color('white')
    ax.spines[spine].set_linewidth(1)
    ax.spines[spine].set_visible(True)

plt.tight_layout(pad=3)
# plt.savefig(r'C:\code\jeff-diz.github.io\images\merge_closest_neighbor\slope_thr_base_mcn_base.png'.format(vt,min_size),
#             facecolor='#19232d',
#             dpi=300)