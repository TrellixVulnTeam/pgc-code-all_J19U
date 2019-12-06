# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 16:36:17 2019

@author: disbr007
"""

import argparse
import logging
import matplotlib.pyplot as plt

import geopandas as gpd

from dataframe_plotting import plot_timeseries_agg, plot_cloudcover

#### Logging setup
# create logger
logger = logging.getLogger('dg_footprint_plotting')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dg_footprint')
    
    args = parser.parse_args()
    
    dg_footprint = args.dg_footprint
    
    dg_footprint = gpd.read_file(dg_footprint)
    
    fig, (ax1, ax2) = plt.subplots(1,2)
    plot_timeseries_agg(dg_footprint, date_col='acqdate', id_col='catalogid', freq='Y', ax=ax1)
    plot_cloudcover(dg_footprint, cloudcover_col='cloudcover', ax=ax2)
    plt.tight_layout()
    plt.show(block=True)
    