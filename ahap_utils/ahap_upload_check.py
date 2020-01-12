# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 14:31:58 2020

@author: disbr007
"""

import os

import pandas as pd

status_csv = r'C:\ahap_upload\ahap_upload_status2020jan10.csv'

master = pd.read_csv(status_csv)

offline = master[master['online']==False]
online = master[master['online']==True]

offline_drives = list(offline['src_drive'].unique())

od_counts = offline.groupby('src_drive').agg({'unique_id':'count'})

print(od_counts)