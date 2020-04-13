# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 12:13:14 2019

@author: disbr007
"""

import pandas as pd

import calendar


def determine_id_col(df):
    '''
    Determines the name of the column holding catalogids from a given dataframe
    '''
    id_cols = ('catalogid', 'CATALOGID', 'CATALOG_ID', 'catalog_id')
    for col in list(df):
        if col in id_cols:
            id_col = col
    return id_col


def determine_stereopair_col(df):
    '''
    Determines the name of the column holding stereopair catalogids from a given dataframe
    '''
    sp_cols = ('STEREOPAIR', 'stereopair', 'stereopair')
    for col in list(df):
        if col in sp_cols:
            sp_col = col
    return sp_col
    


def det_cc_cat(x):
    if x <= 20:
        cc_cat = 'cc20'
    elif x <= 30:
        cc_cat = 'cc21-30'
    elif x <= 40:
        cc_cat = 'cc31-40'
    elif x <= 50:
        cc_cat = 'cc41-50'
    else:
        cc_cat = 'over_50'
    
    return cc_cat


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
    df['temp_date'] = df[date_col]
    date_col = 'temp_date'
    df[date_col] = pd.to_datetime(df[date_col])
#    print(df[date_col])
#    print(df.dtypes)
    df['Month'] = df[date_col].dt.month
    if abbrev == True:
        df['Month'] = df['Month'].apply(lambda x: calendar.month_abbr[x])
    df.drop(columns=[date_col], inplace=True)
    
     
def create_year_col(df, date_col):
    '''takes a dataframe and it's date column and creates a column with the year'''
    df['temp_date'] = df[date_col]
    date_col = 'temp_date'
    df[date_col] = pd.to_datetime(df[date_col])
    df['Year'] = df[date_col].dt.year
    df.drop(columns=[date_col], inplace=True)


def create_day_col(df, date_col):
    '''takes a dataframe and it's date column and creates a column with the day of the month'''
    df['temp_date'] = df[date_col]
    date_col = 'temp_date'
    df[date_col] = pd.to_datetime(df[date_col])
    df['Day'] = df[date_col].dt.day
    df.drop(columns=[date_col], inplace=True)
    

def convert_datetime_to_string(df):
    '''converts any datetime column in df to a string'''
    df[df.select_dtypes(['datetime']).columns] = df[df.select_dtypes(['datetime']).columns].astype(str)


def dbf2DF(dbfile, upper=True): #Reads in DBF files and returns Pandas DF
    '''
    reads a dbf file into a pandas dataframe
    dbfile  : DBF file - Input to be imported
    upper   : Condition - If true, make column heads upper case
    '''
    import pysal as ps
    db = ps.open(dbfile) #Pysal to open DBF
    d = {col: db.by_col(col) for col in db.header} #Convert dbf to dictionary
    pandasDF = pd.DataFrame(d) #Convert to Pandas DF
    if upper == True: #Make columns uppercase if wanted 
        pandasDF.columns = map(str.upper, db.header) 
    db.close() 
    return pandasDF
    