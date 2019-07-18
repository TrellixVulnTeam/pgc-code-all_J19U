# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 14:35:18 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1 import make_axes_locatable
import random, argparse, os, logging


def calc_rmse(l1, l2):
    '''
    Calculates RMSE of two lists of numbers.
    '''

    diffs = [x - y for x, y in zip(l1, l2)]
    sq_diff = [x**2 for x in diffs]
    mean_sq_diff = sum(sq_diff) / len(sq_diff)
    rmse_val = np.sqrt(mean_sq_diff)
    
    return rmse_val


unaligned = gpd.read_file(r'V:\pgc\data\scratch\jeff\brash_island\dem\unaligned.shp')
aligned = gpd.read_file(r'V:\pgc\data\scratch\jeff\brash_island\dem\aligned.shp')


#### Plot
plt.style.use('ggplot')
fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8,8))
#fig.suptitle('RMSE: {:.3f}'.format(rmse_val))

## Histogram of differences
alpha = 0.75
unaligned['Diff'].hist(bins=25, ax=ax, edgecolor='w', alpha=alpha)
aligned['Diff'].hist(bins=25, ax=ax, edgecolor='w', alpha=alpha)

ax.set_yscale('log')
ax.set_xlabel('Elevation Difference')


handles = [Rectangle((0,0),1,1, color='#E24A33', ec='w', alpha=alpha), Rectangle((0,0),1,1, color='#348ABD', ec='w', alpha=alpha)]
labels = ['Unaligned', 'Aligned']
plt.legend(handles, labels)
plt.tight_layout()
