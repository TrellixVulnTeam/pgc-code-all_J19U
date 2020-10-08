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
    parser.add_argument('--dg_footprint')
    parser.add_argument('--date_col', default='acqdate')
    parser.add_argument('--id_col', default='catalogid')
    parser.add_argument('--cloudcover_col', default='cloudcover')
    parser.add_argument('--plot_style', default='ggplot')

    args = parser.parse_args()

    dg_footprint = args.dg_footprint
    date_col = args.date_col
    id_col = args.id_col
    cloudcover_col = args.cloudcover_col
    plot_style = args.plot_style

    dg_footprint = gpd.read_file(dg_footprint)

    try:
        plt.style.use(plot_style)
    except:
        pass

    try:
        fig, (ax1, ax2) = plt.subplots(1, 2)
        plot_timeseries_agg(dg_footprint, date_col=date_col, id_col=id_col, freq='Y', ax=ax1)
        plot_cloudcover(dg_footprint, cloudcover_col=cloudcover_col, ax=ax2)
        plt.tight_layout()
        plt.show(block=True)
    except KeyError as e:
        logger.error('Field not found in footprint. Fields in footprint:\n{}'.format('\n'.join(list(dg_footprint))))
        logger.error(e)
