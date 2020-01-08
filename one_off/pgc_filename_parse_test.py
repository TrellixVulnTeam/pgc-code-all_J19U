# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:08:22 2020

@author: disbr007
"""
import os

t = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\raw\1\QB02_20050724225630_1010010004654800_05JUL24225630-M1BS-052560072400_01_P002.ntf'

f = os.path.basename(t)

scene_id = f.split('.')[0]
first, prod_code, _third = scene_id.split('-')
platform, _date, catalogid, _date_words = first.split('_')

date = '{}-{}-{}'.format(_date[:4], _date[4:6], _date[6:8])

acq_time = '{}T{}:{}:{}'.format(date, _date[8:10], _date[10:12], _date[12:14])

date_words = _date_words[:8]


