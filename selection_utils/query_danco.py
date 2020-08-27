# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""
# TODO:
# -Refactor this so that danco tables are Class, that can then be counted, listed, queried, etc.
# -add chunksize support: 
#    sql = "SELECT * FROM My_Table"
#    for chunk in pd.read_sql_query(sql , engine, chunksize=5):
#        print(chunk)


import os

import geopandas as gpd
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, pool

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')

## Credentials for logging into danco
# TODO: Fix this
PRJ_DIR = os.path.dirname(os.path.dirname(__file__))
creds = []
with open(os.path.join(PRJ_DIR, 'config', 'cred.txt'), 'r') as cred:
    content = cred.readlines()
    for line in content:
        creds.append(str(line).strip())


def list_danco_footprint(instance='danco.pgc.umn.edu'):
    '''
    queries the danco footprint database, returns all layer names in list
    '''
    global logger
    logger.warning('list_danco_footprint depreciated, use list_danco_db() instead.')
    logger.debug('Listing danco.footprint databse tables...')
    connection = None
    try:
        # danco = "danco.pgc.umn.edu"
        print(creds[0])
        connection = psycopg2.connect(user=creds[0],
                                      password=creds[1],
                                      host=instance,
                                      database="footprint")
        cursor = connection.cursor()
        cursor.execute("""SELECT table_name FROM information_schema.tables""")
        tables = cursor.fetchall()    
        tables = [x[0] for x in tables]
        tables = sorted(tables)
        return tables
    
    except (Exception, psycopg2.Error) as error :
        logger.error("Error while connecting to PostgreSQL\n", error)
        raise error
    
    finally:
        # Close database connection.
        if connection:
           connection.close()
           connection = None
           logger.debug("PostgreSQL connection closed.")


def list_danco_db(db, instance='danco.pgc.umn.edu'):
    '''
    queries the danco footprint database, returns all layer names in list
    '''
    global logger
    logger.debug('Listing danco.{} tables...'.format(db))
    connection = None
    try:
        connection = psycopg2.connect(user=creds[0],
                                      password=creds[1],
                                      host=instance,
                                      database=db)
        cursor = connection.cursor()
        cursor.execute("""SELECT table_name FROM information_schema.tables""")
        tables = cursor.fetchall()    
        tables = [x[0] for x in tables]
        tables = sorted(tables)
        
        return tables
    
    
    except (Exception, psycopg2.Error) as error :
        logger.error("Error while connecting to PostgreSQL\n", error)
        raise error
    
    finally:
#        return tables
        # Close database connection.
        if connection:
            connection.close()
            connection = None
            logger.debug("PostgreSQL connection closed.")


def query_footprint(layer, instance='danco.pgc.umn.edu', db='footprint', creds=[creds[0], creds[1]], 
                    table=False, sql=False,
                    where=None, columns=None, orderby=None, orderby_asc=False, 
                    limit=None, offset=None, noh=False, catid_field='catalogid',
                    dryrun=False):
    '''
    queries the danco footprint database, for the specified layer and optional where clause
    returns a dataframe of match
    layer: danco layer to query - e.g.: 'dg_imagery_index_stereo_cc20'
    instance: host to query
    db: database to query
    creds: tuple of (username, password)
    table: True to omit geometry
    sql: SQL statement to override all other passed SQL parameters
    where: sql where clause     - e.g.: "acqdate > '2015-01-21'"
    columns: list of column names to load
    orderby: column to sort returned dataframe by, done at the postgres level
    orderby_asc: if orderby, order ascending if True
    limit: limit number of records returned
    offset: number of records to offset from beginning of table
    noh: Return only records not in pgc_imagery_catalogids
    catid_field: Field in layer to compare to pgc_imagery_catalogids, default: catalogid
    dryrun: print SQL statement without running.
    '''
    global logger
    logger.debug('Querying danco.{}.{}'.format(db, layer))
    connection = None
    try:
        db_tables = list_danco_db(db=db, instance=instance)
        
        if layer not in db_tables:
            logger.warning('{} not found in {}'.format(layer, db))

        engine = create_engine('postgresql+psycopg2://{}:{}@{}/{}'.format(creds[0], creds[1], instance, db),
                               poolclass=pool.NullPool)

#        engine = create_engine('postgresql+psycopg2://{}:{}@{}/{}'.format(creds[0], creds[1], instance, db))
        connection = engine.connect()

        if connection:
            if not sql:
                sql = generate_sql(layer=layer, columns=columns, where=where, orderby=orderby,
                                   orderby_asc=orderby_asc, limit=limit, offset=offset, noh=noh,
                                   catid_field=catid_field, table=table)
                
            if not dryrun:
                # Create pandas df for tables, geopandas df for feature classes
                logger.debug('SQL statement: {}'.format(sql))
                if table == True:
                    df = pd.read_sql_query(sql, con=engine)
                else:
                	# TODO: Fix hard coded epsg
                    logger.debug('SQL: {}'.format(sql))
                    # print(sql)
                    df = gpd.GeoDataFrame.from_postgis(sql, connection, geom_col='geom', crs='epsg:4326')
                
                return df
            else:
                logger.info('SQL: {}'.format(sql))

    except psycopg2.Error as error:
        logger.debug("Error while connecting to PostgreSQL", error)
        logger.debug("SQL: {}".format(sql))
        raise error

    finally:
        # Close database connection.
        if connection:
            connection.close()
            connection = None
            logger.debug("PostgreSQL connection closed.")
    

def table_sample(layer, db='footprint', n=5, table=False, sql=False, where=None, 
                 columns=None, orderby_asc=False, offset=None, dryrun=False):
    
    sample = query_footprint(layer, db=db, table=table, sql=sql, where=where, 
                             columns=columns, orderby="random()", limit=n)
    
    return sample
    
    
def count_table(layer, db='footprint', distinct=False, distinct_col=None, 
                instance='danco.pgc.umn.edu', cred=[creds[0], creds[1]], 
                noh=False, where=None, table=True):
    logger.debug('Querying danco.{}.{}'.format(db, layer))
    connection = None
    try:
        db_tables = list_danco_db(db)
        
        if layer not in db_tables:
            logger.error('{} not found in {}'.format(layer, db))


        connection = psycopg2.connect(user=creds[0],
                                      password=creds[1],
                                      host=instance,
                                      database=db)
        cursor = connection.cursor()

        if connection:
            # cols_str = '*' # select all columns
            sql = generate_sql(layer=layer, where=where, noh=noh, table=True)
            sql = sql.replace('SELECT *', 'SELECT COUNT(*)')
                
            logger.debug('SQL: {}'.format(sql))
            cursor.execute(sql)
            result = cursor.fetchall()
            count = [x[0] for x in result][0]
            
            logger.debug('Query will result in {:,} records.'.format(count))
            
            return count
        
            
    except (Exception, psycopg2.Error) as error :
        logger.debug("Error while connecting to PostgreSQL", error)
        raise error

    finally:
        # Close database connection.
        if connection:
            connection.close()
            connection = None
            logger.debug("PostgreSQL connection closed.")
    
    
def footprint_fields(layer, db='footprint', table=False):
    '''
    DEPREC. -- Use layer_fields
    Gets fields in a danco layer by loading with an SQL
    query that returns only one result (for speed).
    '''
    logger.warning('footprint_fields function depreciated. Use "layer_fields" instead.')
    footprint = query_footprint(layer, db=db, table=table, where="objectid = 1")
    fields = list(footprint)
    return fields


def layer_fields(layer, db='footprint'):
    '''
    Gets fields in a danco layer by loading with an SQL
    query that returns only one result (for speed).
    '''
    layer = query_footprint(layer, db=db, table=True, limit=1)
    fields = list(layer)
    return fields


def layer_crs(layer, db='footprint'):
    """
    Returns the crs of the given layer in the given db.
    
    Parameters
    ----------
    layer : str
        table name in danco db.
    db : str
        database name in danco.

    Returns
    -------
    dict : crs of layer.
    """
    layer = query_footprint(layer=layer, db=db, limit=1)
    crs = layer.crs
    
    return crs
    
    
def stereo_noh(where=None, noh=True):
    '''
    Returns a dataframe with all intrack stereo not on hand as individual rows, 
    rather than as pairs.
    where: string of SQL query syntax
    '''
    # TODO: Fix this - geometry is for catalogid/left, not stereopair. Look up stereopair in index_dg?
    # Use all stereo layer, get both catalogid column and stereopair column
    left = query_footprint('dg_imagery_index_stereo', where=where)
    right = left.drop(columns=['catalogid'])
    right.rename(index=str, columns={'stereopair': 'catalogid'}, inplace=True)

    stereo = pd.concat([left, right], sort=True)
    # Remove ids on hand
    if noh:
        logger.debug('Removing on hand IDs')
        pgc_archive = query_footprint(layer='pgc_imagery_catalogids_stereo', table=True)
        oh_ids = list(pgc_archive.catalog_id)
        del pgc_archive
        # left = left[~left.catalogid.isin(oh_ids)]
        # right = right[~right.catalogid.isin(oh_ids)]
        stereo = stereo[~stereo.catalogid.isin(oh_ids)]
    # Combine columns
    # noh = pd.concat([left, right], sort=True)
    del left, right

    stereo.drop_duplicates(subset='catalogid', inplace=True)

    return stereo


def mono_noh(where=None, noh=True):
    '''
    To determine mono not on hand, remove all stereo catalogids from all dg ids
    returns a dataframe of just mono imagery not on hand (stereo removed)
    where:    sql query
    '''
    # TODO: This table is not updating currently - workaround
    # # All stereo catalogids in one column
    # all_stereo = 'dg_stereo_catalogids_with_pairname'
    # all_stereo = query_footprint(all_stereo, where=where)

    # Workaround to get all stereo catids
    all_stereo = stereo_noh(where=where, noh=True)

    # All ids
    all_mono_stereo = query_footprint('index_dg', where=where)

    # Remove stereo
    mono = all_mono_stereo[~all_mono_stereo['catalogid'].isin(all_stereo['catalogid'])]

    if noh:
        # Remove onhand
        pgc_archive = query_footprint(layer='pgc_imagery_catalogids_stereo', table=True)
        oh_ids = set(pgc_archive.catalog_id)
        mono = mono[~mono['catalogid'].isin(oh_ids)]

    return mono


def all_noh(where=None, cc20=True):
    '''
    returns a dataframe or optionally a list of all ids not on hand (stereo + mono)
    where:    sql query
    cc20:     restrict to cc20
    '''
    # Get all on hand ids
    pgc_archive = query_footprint(layer='pgc_imagery_catalogids', table=True)
    oh_ids = tuple(pgc_archive.catalog_id)
    del pgc_archive
    
    # Get all not on hand: ids in database not in pgc archive
    noh_where = "catalogid NOT IN {}".format(oh_ids)
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
        oh_ids = tuple(pgc_archive.catalog_id)
        del pgc_archive
        
        IK01 = query_footprint('index_ge', where=where)
#        lut = archive_id_lut('IK01')
#        IK01['catalogid'] = IK01['strip_id'].map(lut)
        
        if onhand == True:
            df = IK01[IK01.strip_id.isin(oh_ids)]
            del IK01
        else:
            # onhand == False
            df = IK01[~IK01.strip_id.isin(oh_ids)]
            del IK01
    else:
        df = query_footprint('index_ge', where=where)
    
    return df


def pgc_ids():
    return query_footprint('pgc_imagery_catalogids', columns=['catalog_id'], table=True)['catalog_id'].values


def generate_sql(layer, columns=None, where=None, orderby=False, orderby_asc=False, distinct=False,
                 limit=False, offset=None, noh=False, catid_field='catalogid', table=False,
                 aoi_path=None):

    # COLUMNS
    if columns:
        cols_str = ', '.join(columns)
    else:
        cols_str = '*' # select all columns
    
    # If table, do not select geometry
    if table == True:
        sql = "SELECT {} FROM {}".format(cols_str, layer)
    else:
        sql = "SELECT {}, encode(ST_AsBinary(shape), 'hex') AS geom FROM {}".format(cols_str, layer)
    
    if noh:
        oh_layer = 'pgc_imagery_catalogids'
        oh_catid_field = 'catalog_id'
        sql += " LEFT JOIN {0} ON {1}.{2} = {0}.{3}".format(oh_layer, layer, catid_field, oh_catid_field)
        null_clause = "{}.{} IS NULL".format(oh_layer, oh_catid_field)
        if where:
            where += " AND {}".format(null_clause)
        else:
            where = null_clause
    # WHERE CLAUSE
    # Custom where
    if not where:
        where = ""
    if where:
        where = " WHERE {}".format(where)
        # sql = sql + sql_where

    # Where AOI bounds
    if aoi_path:
        aoi_where = generate_aoi_where(aoi_path=aoi_path, x_fld='x1', y_fld='y1')
        if where:
            where += " AND "
        else:
            where = " WHERE "
        where += aoi_where

    if where:
        sql += where

    # ORDERBY
    if orderby:
        if orderby_asc:
            asc = 'ASC'
        else:
            asc = 'DESC'
        sql_orderby = " ORDER BY {} {}".format(orderby, asc)
        sql += sql_orderby
    
    # LIMIT number of rows
    if limit:
        sql_limit = " LIMIT {}".format(limit)
        sql += sql_limit
    if offset:
        sql_offset = " OFFSET {}".format(offset)
        sql += sql_offset

    logger.debug('Generated SQL:\n{}'.format(sql))
    
    return sql


def generate_rough_aoi_where(aoi_path, x_fld, y_fld, pad=20.0):
    aoi = gpd.read_file(aoi_path)
    minx, miny, maxx, maxy = aoi.total_bounds
    aoi_where = "({0} >= {1} AND {0} <= {2} AND {3} >= {4} AND {3} <= {5})".format(x_fld, minx - pad, maxx + pad,
                                                                                   y_fld, miny - pad, maxy + pad)

    return aoi_where