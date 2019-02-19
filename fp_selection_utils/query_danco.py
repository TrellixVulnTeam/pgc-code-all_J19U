# -*- coding: utf-8 -*-
"""
Created on Thu Jan 17 12:43:09 2019

@author: disbr007
"""

import psycopg2
import geopandas as gpd
from sqlalchemy import create_engine

creds = []
with open(r"C:\Users\disbr007\scripts\cred.txt", 'r') as cred:
    content = cred.readlines()
    for line in content:
        creds.append(str(line).strip())

def query_footprint(layer, where=None):
    '''queries the danco footprint database, for the specified layer and optional where clause
    where clause e.g.: "acqdate > '2015-01-01'" '''
    try:
        connection = psycopg2.connect(user = creds[0],
                                      password = creds[1],
                                      host = "danco.pgc.umn.edu",
                                      database = "footprint")
        
        engine = create_engine('postgresql+psycopg2://disbr007:ArsenalFC10@danco.pgc.umn.edu/footprint')
        
        connection = engine.connect()
#        layer = 'dg_imagery_index_stereo_cc20'
        sql = "SELECT *, encode(ST_AsBinary(shape), 'hex') AS geom FROM {} where {}".format(layer, where)
        df = gpd.GeoDataFrame.from_postgis(sql, connection, geom_col='geom')
        return df
    except (Exception, psycopg2.Error) as error :
        print ("Error while connecting to PostgreSQL", error)
    
    finally:
        #closing database connection.
            if (connection):
                connection.close()
                print("PostgreSQL connection is closed")
