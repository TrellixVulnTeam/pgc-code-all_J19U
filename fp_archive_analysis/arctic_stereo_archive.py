# -*- coding: utf-8 -*-
"""
Created on Tue Oct  8 16:45:52 2019

@author: disbr007
"""

import geopandas as gpd
import logging
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import os
import numpy as np

from query_danco import query_footprint


## Logging
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s -- %(levelname)s: %(message)s')
logging.basicConfig(format='%(asctime)s -- %(levelname)s: %(message)s', 
                    level=logging.INFO)


outdir = r'E:\disbr007\imagery_archive_analysis\arctic_stereo_rate_2019oct08'
write_shp = False

load_shp = True
out_shp = os.path.join(outdir, 'arctic_stereo2019oct10.shp')
if load_shp == True:
    arctic_fp = gpd.read_file(out_shp)

load_pkl = False
pkl_p = os.path.join(outdir, 'arctic_stereo_cc20.pkl')
if load_pkl == True:
    arctic_fp = pd.read_pickle(pkl_p)


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


def locate_fp(cent, aoi):
    """
    Determine if centroid for feature is in aoi.
    """
#    cent = row.geometry.centroid
#    print(list(cent))
    return aoi.geometry.contains(cent)


logger.info('Loading data...')
polar_aoi = query_footprint('pgc_polar_regions')
arctic = polar_aoi[polar_aoi['loc_name']=='Arctic']

if (load_pkl == False) and (load_shp == False):
    load_cols = ['catalogid', 'acqdate', 'cloudcover', 'sqkm_utm']
    fp = query_footprint('dg_imagery_index_stereo_cc20', where="y1 > 35", columns=load_cols)

    logger.info('Determining arctic footprints...')
#    fp['arctic'] = fp.geometry.apply(lambda x: locate_fp(x, arctic))
#    arctic_fp = fp[fp['arctic']==True]
#    arctic_fp.drop(columns=['arctic'], inplace=True)
    
#    arctic_fp = gpd.sjoin(fp, arctic, how='inner')
#    arctic_fp = arctic_fp[load_cols]
    
    arctic_geom = arctic.geometry.values[0]
    fp['arctic'] = fp.geometry.within(arctic_geom)
    arctic_fp.to_pickle(pkl_p)


# Write arctic footprint to file for mapping
if write_shp == True:
    logger.info('Writing shapefile...')
    arctic_fp.to_file(out_shp, driver='ESRI Shapefile')

#### Plot rates and area
# Aggregate by year
logger.info('Aggregating...')
arctic_fp['acqdate'] = pd.to_datetime(arctic_fp['acqdate'])
arctic_fp.set_index('acqdate', inplace=True)
agg = {'catalogid':'nunique', 'sqkm_utm':'sum'}
yearly = arctic_fp.groupby(pd.Grouper(freq='M')).agg(agg)


plt.style.use('ggplot')
fig, (ax1, ax2) = plt.subplots(1,2, figsize=(14,7))

yearly['catalogid'].plot.area(ax=ax1, alpha=0.75)
yearly['sqkm_utm'].plot.area(ax=ax2, alpha=0.75)
#ax1.plot(yearly['catalogid'])
#ax2.plot(yearly['sqkm_utm'])

fig.suptitle('Arctic Stereo Archive', fontsize=16)
ax1.set_ylabel('Pairs')
ax2.set_ylabel('Square Kilometers')

ax_fmtter = FuncFormatter(y_fmt)
for ax in (ax1, ax2):
    ax.yaxis.set_major_formatter(ax_fmtter)
    ax.set_xlim('2007-01-01', '2019-12-31')
    ax.set_xlabel('')

fig.tight_layout(rect=[0, 0.03, 1, 0.95])
#plt.tight_layout()
#fp[:1000].geometry.centroid.plot(ax=ax)
#arctic_fp.geometry.centroid.plot(ax=ax)
#arctic.plot(ax=ax, color='', edgecolor='r')








