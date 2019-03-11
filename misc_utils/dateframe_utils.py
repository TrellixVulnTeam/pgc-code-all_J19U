# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 12:13:14 2019

@author: disbr007
"""

import pandas as pd
import calendar

def fill_dates(df, freq, date_col=None, date_index=False):
    '''takes a dataframe and it's date column and fills in any missing dates at defined
    frequency with null values'''
    if date_index == False:
        start = min(df[date_col])
        end = max(df[date_col])
        date_range = pd.date_range(start=start, end=end, freq=freq)
        df = df.set_index(date_col)
        df = df.reindex(date_range, fill_value=0)
    else:
        start = df.index.min()
        end = df.index.max()
        date_range = pd.date_range(start=start, end=end, freq=freq)
        df = df.reindex(date_range, fill_value=0)
        
def create_month_col(df, date_col):
    '''takes a dataframe and it's date column and returns a column with the month abbreviation'''
    df['Month'] = df[date_col].month
    df['Month'] = df['Month'].apply(lambda x: calendar.month_abbr[x])
    