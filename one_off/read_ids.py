# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 13:27:42 2019

@author: disbr007
"""

import sys, os
from tqdm import tqdm

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import read_ids


mono_refresh = read_ids(r"E:\disbr007\imagery_orders\PGC_order_2019apr11_polar_hma_above_refresh\PGC_order_2019apr112019apr11master.txt")

ordered_path = r'E:\disbr007\imagery_orders\ordered'

ordered = []
for f in os.listdir(ordered_path):
    f_path = os.path.join(ordered_path, f)
    order_ids = read_ids(f_path)
    for an_id in order_ids:
        ordered.append(an_id)
        
no_dup = [x for x in tqdm(mono_refresh) if x not in ordered]
        
