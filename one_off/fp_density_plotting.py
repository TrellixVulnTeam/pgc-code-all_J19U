# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 15:52:49 2019

@author: disbr007
"""

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


density_path = r'E:\disbr007\scratch\density_debug\arc_density.shp'
driver = 'ESRI Shapefile'
density = gpd.read_file(density_path, driver=driver)

mpl.style.use('ggplot')
fig, ax = plt.subplots(1, 1)
fig.patch.set_facecolor('#333333')
ax.set_facecolor('#B3B3B3')

bins=[0, 20, 50, 100, 250, 500, 1000, 1500]
fntsz = 12
ax.hist([np.clip(density['count'], bins[0], bins[-1])], bins=bins, edgecolor='white') #color='#D08429',
#ax.hist(density['count'], bins=10, edgecolor='white') #color='#D08429',

#bin_names = ['0', '5', '10', '20', '50', '100', '370']
bin_names = [str(x) for x in bins]
bin_names[-1] = '2600'
plt.xticks(bins, bin_names)
ax.set_xticklabels(bin_names)
plt.xlabel(xlabel='Stereo Pairs', fontsize=fntsz)
plt.ylabel(ylabel='Number of Points', fontsize=fntsz)
plt.xticks(fontsize=fntsz)
plt.yticks(fontsize=fntsz)
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.tick_params(colors='white')
plt.tight_layout()
plt.savefig(r"E:\disbr007\imagery_archive_analysis\density\airport\stereo_onhand_histo.png", facecolor=fig.get_facecolor())