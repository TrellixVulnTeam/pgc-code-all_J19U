# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 14:50:54 2019

@author: disbr007
"""

import os
from id_parse_utils import write_ids

src_p = r'E:\disbr007\UserServicesRequests\Projects\bjones\1627\3970\Jones_Beavers_Baldwin_Pen_images.txt'

with open(src_p, 'r') as src:
    content = src.read()
    
ids = content.split(', ')
ids = [x.strip() for x in ids]


write_ids(ids, os.path.join(os.path.dirname(src_p), '{}_cleaned.txt'.format(os.path.basename(src_p).split('.')[0])))