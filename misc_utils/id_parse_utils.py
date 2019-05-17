# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""

def read_ids(txt_file, sep=None):
    '''reads ids, one per line, from a text file and returns a list of ids'''
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            if sep:
                # Assumes id is first
                the_id = line.split(sep)[0]
                the_id = the_id.strip()
            else:
                the_id = line.strip()
            ids.append(the_id)
    return ids

def write_ids(ids, out_path):
    with open(out_path, 'w') as f:
        f.write('catalogids\n')
        for each_id in ids:
            f.write('{}\n'.format(each_id))

def date_words(date=None, today=False):
    '''get todays date and convert to '2019jan07' style for filenaming'''
    from datetime import datetime, timedelta
    if today == True:
        date = datetime.now() - timedelta(days=1)
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    year = date.strftime('%Y')
    month = date.strftime('%b').lower()
    day = date.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date