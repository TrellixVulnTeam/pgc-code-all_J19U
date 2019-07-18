# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 10:22:07 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import logging, os
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from archive_analysis_utils import get_count_loop, get_count
from query_danco import query_footprint


## Set up logging
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)
lso = logging.StreamHandler()
lso.setLevel(logging.INFO)
lso.setFormatter(formatter)
logger.addHandler(lso)


## Parameters
project_dir = r'E:\disbr007\imagery_archive_analysis\antarctic_dems'
driver = 'ESRI Shapefile'

## Read in data
# Geocells
gc_p = r'E:\disbr007\general\geocell\geocells_thirty_six.shp'
#gc_p = r'E:\disbr007\scratch\antarctic_aoi_132km_.shp'
gc = gpd.read_file(gc_p, driver=driver)
gc = gc[gc.COUNTRY == 'ANTARCTICA']


# Footprint
it_p = os.path.join(project_dir, 'pkl', 'it_release_status.2019jul11.pkl')
it = pd.read_pickle(it_p)

xt_p = os.path.join(project_dir, 'pkl', 'xt_release_status.2019jul11.pkl')
xt = pd.read_pickle(xt_p)



## Compute density
logging.info('Computing density...')
density_all = get_count(gc, xt)
density_rel = get_count(gc, xt[xt.released == 'released'])
density_unr = get_count(gc, xt[xt.released == 'unreleased'])


## Write results
geocell_scale = 'thirty_six'
density_all.to_file(os.path.join(project_dir, 'shapefile', 'xt11_12_density_{}_all.shp'.format(geocell_scale)), driver=driver)
density_rel.to_file(os.path.join(project_dir, 'shapefile', 'xt11_12_density_{}_rel.shp'.format(geocell_scale)), driver=driver)
density_unr.to_file(os.path.join(project_dir, 'shapefile', 'xt11_12_density_{}_unr.shp'.format(geocell_scale)), driver=driver)


## Plot
# Put dfs in dict with names
dfs = {
#       'All Pairs': density_all,
       'Released Pairs': density_rel,
       'Unreleased Pairs': density_unr,
       }
# Load coastline
cst = gpd.read_file(r'E:\disbr007\imagery_archive_analysis\antarctic_dems\shapefile\addv2_coastlines_dissolved_singlefeature.shp', driver=driver)
# Get min and max counts for plot colors
vmin = min([df['count'].min() for name, df in dfs.items()])
#vmax = max([df['count'].max() for name, df in dfs.items()])
vmax = 100

# Styling
plt.style.use('ggplot')
plt.rcParams['xtick.labelbottom'] = False
plt.rcParams['ytick.labelleft'] = False
cmap = 'gist_heat_r' #'hot_r'
# Set up figure
fig, axes = plt.subplots(nrows=1, ncols=len(dfs))
ax_col = 0


for name, df in dfs.items():
    # Set current ax
    ax = axes[ax_col]
    # Reproject
    df = df.to_crs({'init':'epsg:3031'})
    # Plot
    df.plot(ax=ax, column='count', cmap=cmap, edgecolor='face', legend=False, vmin=vmin, vmax=vmax)
#    cst.plot(ax=ax, color='', edgecolor='black')
    ax.set_title(name)
    ax_col += 1
    
cax = fig.add_axes([0.1, 0.05, 0.8, 0.03])
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
sm._A = []
fig.colorbar(sm, cax=cax, orientation='horizontal')
plt.tight_layout(rect=[0.1, 0.1, 0.9, 0.9])




