# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 12:13:03 2019

@author: disbr007
AHAP Imagery Copier
Copies imagery from server to local location based on selection shapefile.
Input: shapefile exported from either AHAP_Photo_Extents or AHAP_Flightlines with
       joined paths from danco imagery databse: imagery.sde.usgs_index_aerial_image_archive
       or without joined paths (requires geopandas for connecting to danco table).
"""

import os
import logging

from osgeo import ogr
import tqdm

from get_creds import get_creds
from gdal_tools import load_danco_table


# create logger with 'spam_application'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


## TODO: Choose medium res or high res for selection - different filepaths - user input
res = 'high'
if res == 'high':
    resolution = 'high_res'
elif res == 'med':
    resolution = 'med_res'
else:
    logger.error('Resolution not found: {}'.format(res))
    
    
driver = ogr.GetDriverByName('ESRI Shapefile')

join_left = 'PHOTO_ID'
join_right = 'UNIQUE_ID'
right_fields = ['UNIQUE_ID', 'FILENAME', 'FILEPATH']

#### Join selection to table with drives
# Path to selection shapefile 
## TODO: Convert to user input
selection_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\3948\ahap\selected_ahap_photo_extents.shp'

# Open shapefile and get lyr, feature count, geom_type
ds_selection = ogr.Open(selection_p)
lyr_selection = ds_selection.GetLayer(0)
feat_count = lyr_selection.GetFeatureCount()
geom_type = lyr_selection.GetGeomType()
srs_selection = lyr_selection.GetSpatialRef()

# Determine selection type based on presence of 'PHOTO_ID' field
lyr_defn = lyr_selection.GetLayerDefn()
fields_selection = [lyr_defn.GetFieldDefn(i).GetName() for i in range(lyr_defn.GetFieldCount())]

if "PHOTO_ID" in fields_selection:
    sel_type = 'Photo_Extents'
else:
    sel_type = 'Flightlines'

# Get all values in left layer join field
left_unique = [lyr_selection.GetFeature(i).GetField(join_left) for i in range(feat_count)]


### Table with paths (right side of join)
db_server = 'danco.pgc.umn.edu'
db_name = 'imagery'
db_user, db_pw = get_creds()
conn_str = "PG: host={} dbname={} user={} password={}".format(db_server, db_name, db_user, db_pw)

db_tbl = 'sde.usgs_index_aerial_image_archive'

#conn = ogr.Open(conn_str)
# join is done via sql
left_unique_str = str(left_unique).replace('[', '').replace(']', '')
# campaign = 'AHAP'?
where = """({}.{} IN ({})) AND ({}.series = '{}')""".format(db_tbl, join_right, left_unique_str, db_tbl, resolution)

lyr_table, _lyr_conn = load_danco_table(db_name, db_tbl, where=where, load_fields=right_fields, username=db_user, password=db_pw)

# Layer defn (right)
lyr_tbl_defn = lyr_table.GetLayerDefn()
# Layer field names (right)
lyr_tbl_fields = [lyr_tbl_defn.GetFieldDefn(i).GetName() for i in range(lyr_tbl_defn.GetFieldCount())]


### Join by creating new layer in memory
## Create datasource
# memory path
#mem_p = '/vsimem/ahap_copier_temp.shp'
mem_p = r'C:\temp\ahap_copier_testing2.shp'
if os.path.exists(mem_p):
    driver.DeleteDataSource(mem_p)
mem_ds = driver.CreateDataSource(mem_p)
out_lyr = mem_ds.CreateLayer("temp", srs=srs_selection, geom_type=ogr.wkbMultiPolygon)

# Add empty fields from selection (left) shapefile
for i in range(lyr_defn.GetFieldCount()):
    field_dfn = lyr_defn.GetFieldDefn(i)
    out_lyr.CreateField(field_dfn)
    
# Add empty fields from selection (right) table
for i in range(lyr_tbl_defn.GetFieldCount()):
    field_dfn = lyr_tbl_defn.GetFieldDefn(i)
    out_lyr.CreateField(field_dfn)
    
# Populate fields from input selection
out_lyr_defn = out_lyr.GetLayerDefn()

# Looping over input (left) features and adding values and adding matching join values
for i in tqdm.tqdm(range(lyr_selection.GetFeatureCount())):
    # Get feature in selection (left)
    feat_selection = lyr_selection.GetFeature(i)
    
    # Get join field value in left
    left_id = feat_selection.GetField(join_left)
    out_feat = ogr.Feature(out_lyr_defn)
    
    # Fields from left
    for field in fields_selection:
        out_feat.SetField(field, feat_selection.GetField(field))
    
    ## Fields from right
    # Reduce right to just feature that matches current left feature join field (left_id)
    lyr_table.SetAttributeFilter("{} = '{}'".format(join_right, left_id))
    # There should only be one feature, another way to access feature in lyr_table??
    for feature in lyr_table:
#        print(feature.GetField(join_right))
        # Loop over each field in right and add values
        for field in lyr_tbl_fields:
            if field in fields_selection:
                pass
            else:
                out_feat.SetField(field, feature.GetField(field))
    
    # Geometry
    geom = feat_selection.GetGeometryRef()
    out_feat.SetGeometry(geom)
    # Create new feature
    
    out_lyr.CreateFeature(out_feat)



#### List necessary drives
# Windows
base_path = r'V:\pgc\data\aerial\usgs\ahap\photos'
res_path = os.path.join(base_path, res)

drive_paths = []

for feat in out_lyr:
    # Get drive
    drive = feat.GetField('src_drive')

    # Get path parts
    roll = feat.GetField('ORDERING_I')
    filename = feat.GetField('filename')
    photo_id = feat.Getfield('unique_id')
    
    # Create path
    drive_paths.append(os.path.join('AHAP Tif files', roll, photo_id))


out_feat = None
out_lyr = None
mem_ds = None

#### Pull from drives
logger.info('Required offline drives for selection: {}'format(drive_paths))


#### Pull from server



