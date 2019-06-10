# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""

import psycopg2
import geopandas as gpd
import pandas as pd
import sys
from sqlalchemy import create_engine, inspect, MetaData

creds = []
with open(r"C:\code\cred.txt", 'r') as cred:
    content = cred.readlines()
    for line in content:
        creds.append(str(line).strip())

def query_footprint(layer, table=False, where=None, columns=None):
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
            # If specific columns are requested, created comma sep string of those columns to pass in sql
            if columns:
                cols_str = ', '.join(columns)
            else:
                cols_str = '*' # select all columns
            
            # If table, do not select geometry
            if table == True:
#                sql = "SELECT * FROM {}".format(layer) # can delete, saved during 'column' debugging
                sql = "SELECT {} FROM {}".format(cols_str, layer)
            else:
                sql = "SELECT {}, encode(ST_AsBinary(shape), 'hex') AS geom FROM {}".format(cols_str, layer)
            
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
    TO TRY: 
        SELECT *
        FROM layer.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = N'Customers'
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


def mono_noh(where=None, cc20=True):
    '''
    returns a dataframe of just mono imagery not on hand (stereo removed)
    where:    sql query
    cc20:     restrict to cc20 only
    '''
    # Get all not on hand
    all_noh = query_footprint('dg_imagery_index_all_notonhand_cc20', where=where)
    # Get all stereopairs
    all_pairs = list(all_noh.stereopair)
    mono_noh = all_noh[(~all_noh.catalogid.isin(all_pairs)) & (all_noh[all_noh.stereopair == 'NONE'])]
    return mono_noh


def all_noh(where=None, cc20=True):
    '''
    returns a dataframe or optionally a list of all ids not on hand (stereo + mono)
    where:    sql query
    cc20:     restrict to cc20
    '''
    # Get all on hand ids
    pgc_archive = query_footprint(layer='pgc_imagery_catalogids', table=True)
    pgc_ids = tuple(pgc_archive.catalog_id)
    del pgc_archive
    
    # Get all not on hand: ids in database not in pgc archive
    noh_where = "catalogid NOT IN {}".format(pgc_ids)
    all_noh = query_footprint('index_dg', where=noh_where)
    return all_noh


def all_IK01(where=None, onhand=None):
    '''
    returns a dataframe of IKONOS imagery footprints
    where:    sql query
    onhand:   if True return only on hand, if False only not on hand, defaults to both
    '''

    def archive_id_lut(sensor):

        # Look up table names on danco
        luts = {
                'GE01': 'index_dg_catalogid_to_ge_archiveid_ge01',
                'IK01': 'index_dg_catalogid_to_ge_archiveid_ik'
                }
        
        # Verify sensor
        if sensor in luts:
            pass
        else:
            print('{} look up table not found. Sensor must be in {}'.format(sensor, luts.keys()))
        
        lu_df = query_footprint(layer=luts[sensor], table=True)
        lu_dict = dict(zip(lu_df.crssimageid, lu_df.catalog_identifier))
    
        return lu_dict    
    
    if where:
        where += " AND source_abr = 'IK-2'"
    else:
        where = "source_abr = 'IK-2'"
    
    if onhand == True or onhand == False:
        # Get all on hand ids
        pgc_archive = query_footprint(layer='pgc_imagery_catalogids', table=True)
        pgc_ids = tuple(pgc_archive.catalog_id)
        del pgc_archive
        
        IK01 = query_footprint('index_ge', where=where)
#        lut = archive_id_lut('IK01')
#        IK01['catalogid'] = IK01['strip_id'].map(lut)
        
        if onhand == True:
            df = IK01[IK01.strip_id.isin(pgc_ids)]
            del IK01
        else:
            # onhand == False
            df = IK01[~IK01.strip_id.isin(pgc_ids)]
            del IK01
    else:
        df = query_footprint('index_ge', where=where)
    
    return df
    
    








