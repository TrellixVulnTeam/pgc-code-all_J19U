# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 12:55:59 2019

@author: disbr007
"""

import tqdm

txt_file = r'C:\pgc_index\catalog_ids.txt'

new_ids = []
with open(txt_file, 'r') as f:
        content = f.readlines()
        for group in content:
            group = group.replace("',", "\n")
            group = group.replace('[', ',')
            group = group.replace(']', ',')
            group = group.replace("'", '\n')
            group_list = group.split('\n')
            rem_vals = [",,", "", ',', ' ', '   ']
            group_list = [x for x in group_list if x not in rem_vals]
            for each_id in group_list:
                new_ids.append(each_id)
                
new_ids = set(new_ids)