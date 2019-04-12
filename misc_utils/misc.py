# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 11:40:46 2019

@author: disbr007
"""

import calendar
from datetime import datetime, timedelta

def date2words(today=False, date=None):
    '''
    get todays date and convert to '2019jan07' style for filenaming
    or take datetime object in and convert to same style
    '''
    if today == True:
        date = datetime.now() - timedelta(days=1)
    else:
        date = date
    year = date.strftime('%Y')
    month = date.strftime('%b').lower()
    day = date.strftime('%d')
    date_words = r'{}{}{}'.format(year, month, day)
    return date_words