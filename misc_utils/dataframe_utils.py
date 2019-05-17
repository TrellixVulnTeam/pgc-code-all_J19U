# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 12:13:14 2019

@author: disbr007
"""

import pandas as pd
import pysal as ps
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
   
     
def create_month_col(df, date_col, abbrev=False):
    '''takes a dataframe and it's date column and creates a column with the month, optionally as
    an abbreviation'''
    df[date_col] = pd.to_datetime(df[date_col])
#    print(df[date_col])
#    print(df.dtypes)
    df['Month'] = df[date_col].dt.month
    if abbrev == True:
        df['Month'] = df['Month'].apply(lambda x: calendar.month_abbr[x])
   
     
def create_year_col(df, date_col):
    '''takes a dataframe and it's date column and creates a column with the year'''
    df[date_col] = pd.to_datetime(df[date_col])
    df['Year'] = df[date_col].dt.year


def dbf2DF(dbfile, upper=True): #Reads in DBF files and returns Pandas DF
    '''
    reads a dbf file into a pandas dataframe
    dbfile  : DBF file - Input to be imported
    upper   : Condition - If true, make column heads upper case
    '''
    db = ps.open(dbfile) #Pysal to open DBF
    d = {col: db.by_col(col) for col in db.header} #Convert dbf to dictionary
    pandasDF = pd.DataFrame(d) #Convert to Pandas DF
    if upper == True: #Make columns uppercase if wanted 
        pandasDF.columns = map(str.upper, db.header) 
    db.close() 
    return pandasDF
    