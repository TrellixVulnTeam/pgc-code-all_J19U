# -*- coding: utf-8 -*-
"""
Created on Fri Jun  7 14:23:32 2019

@author: disbr007
missing ids analysis by order based on sheet
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys

sys.path.insert(0, r'C:\code\img_orders')
from ids_order_sources import lookup_id_order, id_order_loc_update


missing_ids = r"E:\disbr007\imagery_archive_analysis\cloudcover\missing_ids_cc0_20.txt"
missing_src = lookup_id_order(missing_ids, all_orders=id_order_loc_update())
missing_src['order'] = missing_src['order'].replace({'PGC_order': 'P', 'NASA-GSFC': 'N'}, regex=True)

orders = missing_src.groupby(['order']).agg({'ids': 'count', 'created': 'first'})
orders.sort_values(by='created', inplace=True)

ids = missing_src.groupby(['ids']).agg({'order': 'count', 'created': 'first'})

## Plot all orders with more than n missing ids
with plt.style.context('seaborn-darkgrid', after_reset=True):
    fig, ax = plt.subplots()
    n = 500
    
    ax = orders[orders.ids > n].plot.barh(y='ids', color='black', ax=ax)
    ax.set_title('Orders containing missing IDs')
    ax.set(xlabel='Number of missing IDs', ylabel='Order')
    ax.get_legend().remove()
    
    plt.gcf().text(0.01, 0.02, 'Orders with more than {} missing ids'.format(n),
            ha='left',
            va='center',
            fontstyle='italic',
            fontsize='small')
    
    fig.tight_layout()
    fig.show()
