# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 12:52:16 2019

@author: disbr007
"""

import arcpy
import os

#def danco_footprint_connection():
#
#creds = []
#with open(r"C:\code\pgc-code-all\cred.txt", 'r') as cred:
#    content = cred.readlines()
#    for line in content:
#        creds.append(str(line).strip())
#
#
#out_folder_path = r'C:\dbconn\arcpy_cxn'
#out_name = r'footprint_arcpy.sde'
#database_platform = 'POSTGRESQL'
#instance = 'danco.pgc.umn.edu'
#account_authentication= 'DATABASE_AUTH'
#username = creds[0]
#password = creds[1]
#save_user_pass = "SAVE_USERNAME"
#database = 'footprint'
#schema = ''
#version_type = 'TRANSACTIONAL'
#version = 'sde.DEFAULT'
#date = ''
#
#
#

#cxn = arcpy.CreateDatabaseConnection_management(
#        out_folder_path=out_folder_path,
#        out_name=out_name,
#        database_platform=database_platform,
#        instance=instance,
#        account_authentication=account_authentication,
#        username=username,
#        password=password,
#        save_user_pass=save_user_pass,
#        database=database,
#        schema=schema,
#        version_type=version_type,
#        version=version,
#        date=date)
#
#
#print('reading tables')
#featClasses = arcpy.ListFeatureClasses()
#tables = arcpy.ListTables()
#for fc in featClasses:
#    print(fc)
#print('\n')
#for tbl in tables:
#    print(tbl)
#    
#
##    return os.path.join(out_folder_path, 'footprint.sde.index.dg')
#
#arcpy.env.workspace = os.path.join('footprint.sde.index_dg', 'in_memory\test')                       
#fc = arcpy.MakeFeatureLayer_management('footprint.sde.index.dg', 'in_memory\index_dg')
#fields = arcpy.ListFields(fc)
#for f in fields:
#    print(f.name)
#



def danco_footprint_connection():
    arcpy.env.overwriteOutput = True

    # Local variables:
    arcpy_cxn = "C:\\dbconn\\arcpy_cxn"
    #arcpy_footprint_MB_sde = arcpy_cxn
    
    # Process: Create Database Connection
    cxn = arcpy.CreateDatabaseConnection_management(arcpy_cxn, 
                                                     "footprint_arcpy.sde", 
                                                     "POSTGRESQL", 
                                                     "danco.pgc.umn.edu", 
                                                     "DATABASE_AUTH", 
                                                     "disbr007", 
                                                     "ArsenalFC10", 
                                                     "SAVE_USERNAME", 
                                                     "footprint", 
                                                     "", 
                                                     "TRANSACTIONAL", 
                                                     "sde.DEFAULT", 
                                                     "")
    
    arcpy.env.workspace = os.path.join("C:\\dbconn\\arcpy_cxn", "footprint_arcpy.sde")
    
#    featClasses = arcpy.ListFeatureClasses()
#    tables = arcpy.ListTables()
#    for fc in featClasses:
#        print(fc)
#    print('\n')
#    for tbl in tables:
#        print(tbl)
    
#    fc = arcpy.MakeFeatureLayer_management('footprint.sde.index_dg', 'in_memory\test')
    
    return 'footprint.sde.index_

fc = danco_footprint_connection()