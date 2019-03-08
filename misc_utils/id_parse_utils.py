# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""

def ids_to_list(ids_path):
    '''read txt/csv of just ids, convert to list'''
    with open(ids_path, 'r') as f:
        ids = []
        lines = f.readlines()
        for line in lines:
            ids.append(line.strip())
            
def date_words():
    '''get todays date and convert to '2019jan07' style for filenaming'''
    import datetime
    now = datetime.datetime.now() - datetime.timedelta(days=1)
    year = now.strftime('%Y')
    month = now.strftime('%b').lower()
    day = now.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date