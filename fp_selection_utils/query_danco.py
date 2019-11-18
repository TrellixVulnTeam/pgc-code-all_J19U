# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""

import sys, logging

import geopandas as gpd
import pandas as pd
import psycopg2
from sqlalchemy import create_engine#, inspect, MetaData


# create logger with 'spam_application'
logger = logging.getLogger('query_danco')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


## Credentials for logging into danco
creds = []
with open(r"C:\code\pgc-code-all\cred.txt", 'r') as cred:
    content = cred.readlines()
    for line in content:
        creds.append(str(line).strip())

def list_danco_footprint():
    '''
    queries the danco footprint database, returns all layer names in list
    '''
    global logger
    logger.debug('Listing danco.footprint databse tables...')
    try:
        danco = "danco.pgc.umn.edu"
        connection = psycopg2.connect(user = creds[0],
                                      password = creds[1],
                                      host = danco,
                                      database = "footprint")
        cursor = connection.cursor()
        cursor.execute("""SELECT table_name FROM information_schema.tables""")
        tables = cursor.fetchall()    
        tables = [x[0] for x in tables]
        tables = sorted(tables)
        return tables
    
    
    except (Exception, psycopg2.Error) as error :
        logger.debug("Error while connecting to PostgreSQL", error)
    
    
    finally:
#        return tables
        # Close database connection.
        if (connection):
            connection.close()
            logger.debug("PostgreSQL connection closed.")


def list_danco_db(db):
    '''
    queries the danco footprint database, returns all layer names in list
    '''
    global logger
    logger.debug('Listing danco.{} tables...'.format(db))
    try:
        danco = "danco.pgc.umn.edu"
        connection = psycopg2.connect(user = creds[0],
                                      password = creds[1],
                                      host = danco,
                                      database = db)
        cursor = connection.cursor()
        cursor.execute("""SELECT table_name FROM information_schema.tables""")
        tables = cursor.fetchall()    
        tables = [x[0] for x in tables]
        tables = sorted(tables)
        
        return tables
    
    
    except (Exception, psycopg2.Error) as error :
        logger.debug("Error while connecting to PostgreSQL", error)
    
    
    finally:
#        return tables
        # Close database connection.
        if (connection):
            connection.close()
            logger.debug("PostgreSQL connection closed.")
            
            
            
def query_footprint(layer, instance='danco.pgc.umn.edu', db='footprint', creds=[creds[0], creds[1]], table=False, where=None, columns=None):
    '''
    queries the danco footprint database, for the specified layer and optional where clause
    returns a dataframe of match
    layer: danco layer to query - e.g.: 'dg_imagery_index_stereo_cc20'
    where: sql where clause     - e.g.: "acqdate > '2015-01-21'"
    columns: list of column names to load
    '''
    global logger
    logger.debug('Querying danco.{}.{}'.format(db, layer))
    try:
        db_tables = list_danco_db(db)
        
        if layer not in db_tables:
            logger.warning('{} not found in {}'.format(layer, db))
        
        ## Temp solution to use sandwhich instance
#        danco = instance
#        danco = "danco.pgc.umn.edu"
#        connection = psycopg2.connect(user = creds[0],
#                                      password = creds[1],
#                                      host = danco,
#                                      database = "footprint")

        engine = create_engine('postgresql+psycopg2://{}:{}@danco.pgc.umn.edu/{}'.format(creds[0], creds[1], db))

#        engine = create_engine('postgresql+psycopg2://{}:{}@{}/{}'.format(creds[0], creds[1], instance, db))
        connection = engine.connect()

        if connection:
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
#
    except (Exception, psycopg2.Error) as error :
        logger.debug("Error while connecting to PostgreSQL", error)
    
    finally:
        # Close database connection.
        if (connection):
            connection.close()
            logger.debug("PostgreSQL connection closed.")


def footprint_fields(layer, db='footprint'):
    '''
    DEPREC. -- Use layer_fields
    Gets fields in a danco layer by loading with an SQL
    query that returns only one result (for speed).
    '''
    logging.warning('footprint_fields function depreciated. Use "layer_fields" instead.')
    footprint = query_footprint(layer, db=db, where="objectid = 1")
    fields = list(footprint)
    return fields


def layer_fields(layer, db):
    '''
    Gets fields in a danco layer by loading with an SQL
    query that returns only one result (for speed).
    '''
    footprint = query_footprint(layer, db=db, table=True, where="objectid = 1")
    fields = list(footprint)
    return fields



def stereo_noh(where=None):
    '''
    Returns a dataframe with all intrack stereo not on hand as individual rows, 
    rather than as pairs.
    where: string of SQL query syntax
    '''
    # Use all stereo layer, get both catalogid column and stereopair column
    left = query_footprint('dg_imagery_index_stereo', where=where)
    right = left.drop(columns=['catalogid'])
    right.rename(index=str, columns={'stereopair': 'catalogid'}, inplace=True)
    
    # Remove ids on hand
    pgc_archive = query_footprint(layer='pgc_imagery_catalogids_stereo', table=True)
    pgc_ids = list(pgc_archive.catalog_id)
    del pgc_archive
    noh_left = left[~left.catalogid.isin(pgc_ids)]
    noh_right = right[~right.catalogid.isin(pgc_ids)]
    
    # Combine columns        
    noh = pd.concat([noh_left, noh_right], sort=True)
    del noh_left, noh_right
    return noh


def mono_noh(where=None):
    '''
    To determine mono not on hand, remove all stereo catalogids from all dg ids
    returns a dataframe of just mono imagery not on hand (stereo removed)
    where:    sql query
    '''
    # All stereo catalogids in one column
    all_stereo = 'dg_stereo_catalogids_with_pairname'
    all_stereo = query_footprint(all_stereo, where=where)
    
    # All ids
    all_mono_stereo = query_footprint('index_dg', where=where)
    
    # Remove stereo
    mono_noh = all_mono_stereo[~all_mono_stereo['catalogid'].isin(all_stereo['catalogid'])]
    
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
    Returns a dataframe of IKONOS imagery footprints
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
