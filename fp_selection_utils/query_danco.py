# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""

import psycopg2
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine

creds = []
with open(r"C:\code\cred.txt", 'r') as cred:
    content = cred.readlines()
    for line in content:
        creds.append(str(line).strip())

def query_footprint(layer, table=False, where=None):
    '''
    queries the danco footprint database, for the specified layer and optional where clause
    returns a dataframe of match
    layer: danco layer to query - e.g.: 'dg_imagery_index_stereo_cc20'
    where: sql where clause     - e.g.: "acqdate > '2015-01-01'"
    '''
    try:
        danco = "danco.pgc.umn.edu"
        connection = psycopg2.connect(user = creds[0],
                                      password = creds[1],
                                      host = danco,
                                      database = "footprint")

        engine = create_engine('postgresql+psycopg2://{}:{}@danco.pgc.umn.edu/footprint'.format(creds[0], creds[1])) # untested, use above if not working
        connection = engine.connect()

        if connection:
            print('PostgreSQL connection to {} at {} opened.'.format(layer, danco))
            # If table, do not select geometry
            if table == True:
                sql = "SELECT * FROM {}".format(layer)
            else:
                sql = "SELECT *, encode(ST_AsBinary(shape), 'hex') AS geom FROM {}".format(layer)
            
            # Add where clause if necessary
            if where:
                sql_where = " where {}".format(where)
                sql = sql + sql_where
                
            # Create pandas df for tables, geopandas df for feature classes
            if table == True:
                df = pd.read_sql_query(sql, con=engine)
            else:
                df = gpd.GeoDataFrame.from_postgis(sql, connection, geom_col='geom', crs={'init' :'epsg:4326'})
            return df
    except (Exception, psycopg2.Error) as error :
        print ("Error while connecting to PostgreSQL", error)
    
    finally:
        # Close database connection.
        if (connection):
            connection.close()
            print("PostgreSQL connection closed.")

def stereo_noh(where=None):
    '''returns a dataframe with all intrack stereo not on hand as individual rows, rather
    than as pairs'''
    stereo_noh_left = 'dg_imagery_index_stereo_notonhand_left_cc20'
    stereo_noh_right = 'dg_imagery_index_stereo_notonhand_right_cc20'
    
    noh_left = query_footprint(stereo_noh_left, where=where)
    noh_right = query_footprint(stereo_noh_right, where=where)
    
    noh_right.rename(index=str, columns={'stereopair': 'catalogid'}, inplace=True)
    
    noh = pd.concat([noh_left, noh_right], sort=True)
    return noh


def mono_noh(where=None):
    # Get all not on hand
    all_noh = query_footprint('dg_imagery_index_all_notonhand_cc20', where=where)
    print(len(all_noh))
    # Get all stereopairs
    all_pairs = list(all_noh.stereopair)
    mono_noh = all_noh[(~all_noh.catalogid.isin(all_pairs)) & (all_noh[all_noh.stereopair == 'NONE'])]
    return mono_noh
