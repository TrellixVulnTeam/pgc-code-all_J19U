# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""

def read_ids(txt_file):
    '''reads ids, one per line, from a text file and returns a list of ids'''
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            ids.append(line.strip())
    return ids

def write_ids(ids, out_path):
    with open(out_path, 'w') as f:
        for each_id in ids:
            f.write('{}\n'.format(each_id))

def date_words():
    '''get todays date and convert to '2019jan07' style for filenaming'''
    import datetime
    now = datetime.datetime.now() - datetime.timedelta(days=1)
    year = now.strftime('%Y')
    month = now.strftime('%b').lower()
    day = now.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date