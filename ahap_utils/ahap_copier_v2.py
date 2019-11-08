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

import argparse
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

## User input
list_drives = True

## TODO: Choose medium res or high res for selection - different filepaths - user input
res = 'high_res'
if res == 'high_res':
    res_dir = 'high'
elif res == 'med_res':
    res_dir = 'med'
else:
    logger.error('Resolution not found: {}'.format(res))
    

driver = ogr.GetDriverByName('ESRI Shapefile')

join_left = 'PHOTO_ID'
join_right = 'UNIQUE_ID'
right_fields = ['UNIQUE_ID', 'FILENAME', 'FILEPATH', 'SRC_DRIVE']

#### Join selection to table with drives
# Path to selection shapefile 
## TODO: Convert to user input
selection_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\3948\ahap\selected_ahap_photo_extents.shp'


# Open shapefile and get lyr, feature count, geom_type
ds_selection = ogr.Open(selection_p)
lyr_selection = ds_selection.GetLayer(0)
feat_count = lyr_selection.GetFeatureCount()
#geom_type = lyr_selection.GetGeomType()
#srs_selection = lyr_selection.GetSpatialRef()

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

# Add where clause construction based on provided arguments (series, campaign, etc.)
where = """({}.{} IN ({})) AND ({}.series = '{}')""".format(db_tbl, join_right, left_unique_str, db_tbl, res)

lyr_table, _lyr_conn = load_danco_table(db_name, db_tbl, where=where, load_fields=right_fields, username=db_user, password=db_pw)

# Layer defn (right)
lyr_tbl_defn = lyr_table.GetLayerDefn()
lyr_tbl_field = [lyr_tbl_defn.GetFieldDefn(i).GetName() for i in range(lyr_tbl_defn.GetFieldCount())]

#### List necessary drives
# Windows
base_path = r'V:\pgc\data\aerial\usgs\ahap\photos'
res_path = os.path.join(base_path, res)

drives = []
drive_paths = []
server_paths = []

for feat in lyr_table:
    # Get drive
    drive = feat.GetField('src_drive')
    if drive not in drives:
        drives.append(drive)

    # Get path parts
    filename = feat.GetField('filename')
    filepath = feat.GetField('filepath')
    photo_id = feat.GetField('unique_id')
    
    # Create drive path
    drive_path = os.path.join('AHAP Tif files', filepath)
    drive_paths.append(drive_path)

    # Create server path
    server_path = os.path.join(base_path, res_dir, I)
    

if list_drives:
    logger.info('Drives: ')
    for d in drives:
        logger.info(d)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('selection', type=str,
                        help='Path to subset from usgs_index_aerial_image_archive')
    
    parser.add_argument('--list_drives', action='store_true',
                        help='Flag to only list drives and not attempt to pull.')
    parser.add_argument('--series', type=str, 
                        help='''Series of campaign to pull: 
                            for most campaigns: "med_res" or "high_res"''')
    parser.add_argument('--campaign', type=str,
                        help='Aerial campaign to copy: "AHAP", "TMA", "LIMA", etc.')
    
    
#### Upload from drives to server (seperate script)



#### Pull from server



#### Pull from drives


