# -*- coding: utf-8 -*-
"""
Select DEMs based on percentage of non-NoData pixels in an AOI and copy from server.
"""

import os
import shutil

import geopandas as gpd

from query_danco import query_footprint
from id_parse_utils import write_ids
from valid_data import valid_percent_clip


# PARAMETERS
PRJ_DIR = r'E:\disbr007\umn\ms'
LEWK_P = r'E:\disbr007\umn\ms\shapefile\tk_loc\lewk_2019_hs.shp'
CATIDS_P = os.path.join(PRJ_DIR, 'dem_catalogids.txt')
DEMS_DIR = os.path.join(PRJ_DIR, 'dems')
SHP_DIR = os.path.join(PRJ_DIR, 'shapefile')
SCRATCH = os.path.join(PRJ_DIR, 'scratch')
aoi_name = 'aoi_2'
DEMS_AOI = os.path.join(DEMS_DIR, aoi_name)
AOI_P = os.path.join(SHP_DIR, 'aois', '{}.shp'.format(aoi_name))
AOI_PRJ = os.path.join(SHP_DIR, 'aois', '{}_prj.shp'.format(aoi_name))
# Threshold percentage of valid data over AOI
VALID_THRESH = 50

DEMS_FP = 'pgc_dem_setsm_strips'


## Load DEM footprints over AOI
# Get CRS of DEMs - this loads no records (fast), but gets the crs
dems_crs = query_footprint(DEMS_FP, where="1=2").crs

# Load all points in AOI
aois = gpd.read_file(AOI_P)
aois = aois.to_crs(dems_crs)
# Get bounds to reduce query size
minx, miny, maxx, maxy = aois.total_bounds
dems_where = """cent_lon > {} AND cent_lon < {} AND 
                cent_lat > {} AND cent_lat < {}""".format(minx-0.25, maxx+0.25, miny-0.25, maxy+0.25)
# Get DEM footprints               
dems = query_footprint(DEMS_FP, where=dems_where)


# Clip to AOIs
# Create directory for clipped DEMs
dem_aoi_sd = os.path.join(DEMS_DIR, aoi_name)
if not os.path.exists(dem_aoi_sd):
    os.makedirs(dem_aoi_sd)
# Add clipped path to dataframe
dems['clipped_path'] = dems['dem_id'].apply(lambda x: os.path.join(dem_aoi_sd, 
                                                                   '{}_clip.tif'.format(x)))
# Create full windows path
dems['full_path'] = dems.apply(lambda x: os.path.join(x['win_path'], x['dem_name']), axis=1)
dems['full_path'] = dems['full_path'].apply(lambda x: x.replace('/', os.sep))
# Check if DEM exists -- keep only those that do
dems['dem_valid'] = dems['full_path'].apply(lambda x: os.path.exists(x))
dems = dems[dems['dem_valid']==True]


# Get valid data percent in AOI
print('getting valid percent...')
dems['valid_perc'] = dems.apply(lambda x: valid_percent_clip(AOI_P, raster=x['full_path']), axis=1)
# Threshold selection
dems = dems[dems['valid_perc']>=VALID_THRESH]


# Get DEMs
# Create outpath
if not os.path.exists(DEMS_AOI):
    os.makedirs(DEMS_AOI)
# Copy DEMs down
for dem_path, dem_name in zip(list(dems['full_path']), list(dems['dem_name'])):
    out_path = os.path.join(DEMS_AOI, dem_name)
    shutil.copy2(dem_path, out_path)

# # Get catalogids associated with DEMs
catalogids = list(dems['catalogid1'])
# Write catalogids out -- for collecting imagery
write_ids(catalogids, CATIDS_P)
