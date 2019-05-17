# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""

import psycopg2
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, inspect, MetaData

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

        engine = create_engine('postgresql+psycopg2://{}:{}@danco.pgc.umn.edu/footprint'.format(creds[0], creds[1]))
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


def list_danco_footprint():
    '''
    ** NOT FUNCTIONAL YET - cannot manage to get a list of layer names back**
    queries the danco footprint database, returns all layer names in list
    '''
    try:
        danco = "danco.pgc.umn.edu"
        connection = psycopg2.connect(user = creds[0],
                                      password = creds[1],
                                      host = danco,
                                      database = "footprint")

        engine = create_engine('postgresql+psycopg2://{}:{}@danco.pgc.umn.edu/footprint'.format(creds[0], creds[1]))
        connection = engine.connect()

        if connection:
            print('PostgreSQL connection to {} opened.'.format(danco))
            tables = []
            inspector = inspect(engine)
            print(type(inspector))

            schemas = inspector.get_schema_names()
            table_names = inspector.get_table_names(schema="disbr007")
            view_names = inspector.get_view_names(schema="disbr007")
            print(table_names, view_names)
    except (Exception, psycopg2.Error) as error :
        print ("Error while connecting to PostgreSQL", error)
    
    finally:
        return tables
        # Close database connection.
        if (connection):
            connection.close()
            print("PostgreSQL connection closed.")


def stereo_noh(where=None, cc20=True):
    '''returns a dataframe with all intrack stereo not on hand as individual rows, rather
    than as pairs'''
    if cc20:
        # Use the prebuilt cc20 not on hand layers
        stereo_noh_left = 'dg_imagery_index_stereo_notonhand_left_cc20'
        stereo_noh_right = 'dg_imagery_index_stereo_notonhand_right_cc20'
        
        noh_left = query_footprint(stereo_noh_left, where=where)
        noh_right = query_footprint(stereo_noh_right, where=where)
        noh_right.rename(index=str, columns={'stereopair': 'catalogid'}, inplace=True)
    
    else:
        # Use all stereo layer, remove ids on hand
        left = query_footprint('dg_imagery_index_stereo', where=where)
        right = left.drop(columns=['catalogid'])
        right.rename(index=str, columns={'stereopair': 'catalogid'}, inplace=True)
                
        pgc_archive = query_footprint(layer='pgc_imagery_catalogids_stereo', table=True)
        pgc_ids = list(pgc_archive.catalog_id)
        del pgc_archive
                
        noh_left = left[~left.catalogid.isin(pgc_ids)]
        noh_right = right[~right.catalogid.isin(pgc_ids)]
            
    noh = pd.concat([noh_left, noh_right], sort=True)
    del noh_left, noh_right
    return noh


def mono_noh(where=None):
    # Get all not on hand
    all_noh = query_footprint('dg_imagery_index_all_notonhand_cc20', where=where)
    print(len(all_noh))
    # Get all stereopairs
    all_pairs = list(all_noh.stereopair)
    mono_noh = all_noh[(~all_noh.catalogid.isin(all_pairs)) & (all_noh[all_noh.stereopair == 'NONE'])]
    return mono_noh
