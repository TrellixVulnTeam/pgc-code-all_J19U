# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:14:51 2019

@author: disbr007
"""

import pickle
import pandas as pd
import os
import calendar

pkl_dir = r'E:\disbr007\imagery_archive_analysis\imagery_rates\2019aug25\pickles'
#pkl_paths = [os.path.join(pkl_dir, f) for f in os.listdir(pkl_dir)]
pkl_paths = [r'E:\disbr007\imagery_archive_analysis\imagery_rates\2019aug25\pickles\Intrack.pkl']

with pd.ExcelWriter(os.path.join(pkl_dir, 'output.xlsx')) as writer:
    for pkl in pkl_paths:
            df = pd.read_pickle(pkl)
            df = df.unstack(['region']).fillna(0)
            df = df.unstack(['cc_cat']).fillna(0)
            df.reset_index('acqdate', inplace=True)
            df['year'] = df['acqdate'].apply(lambda x: x.year)
            df['month'] = df['acqdate'].dt.strftime('%b')
            df.sort_values(by='acqdate', inplace=True)
            df['year'] = df['year'].drop_duplicates()
            
            df.to_excel(writer, sheet_name=os.path.basename(pkl).split('.')[0])
