# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import os
import pandas as pd
import geopandas as gpd

from query_danco import query_footprint

prj_dir = r'E:\disbr007\UserServicesRequests\Projects\bjones\1666\4084'
bore_p = os.path.join(prj_dir, r'Permafrost_Borehole_Sites.shp')
utm_p = r'E:\disbr007\general\UTM_Zone_Boundaries\UTM_Zone_Boundaries.shp'
sel_dir = os.path.join(prj_dir, 'epsg')


bore = gpd.read_file(bore_p)
utm = gpd.read_file(utm_p)

bore = gpd.sjoin(bore, utm, how='left')
bore['epsg'] = bore['ZONE'].apply(lambda x: '269{}'.format(x))

# Create shapefile of each utm zone
for zone in bore['epsg'].unique():
    bore_zone = bore[bore['epsg']==zone]
    # bore_zone.to_file(os.path.join(prj_dir, 'pbs_{}.shp'.format(zone)))

# bore.to_file(os.path.join(prj_dir, 'pbs_utm_zones.shp'))
master_sel = gpd.GeoDataFrame()
for f in os.listdir(sel_dir):
    if f.endswith('.shp'):
        sel = gpd.read_file(os.path.join(sel_dir, f))
        sel['epsg'] = f.split('_')[1].split('.')[0]
        master_sel = pd.concat([master_sel, sel])

master_sel = master_sel.drop_duplicates(subset=['scene_id'])
master_sel.to_file(os.path.join(prj_dir, 'mfp_sel_all_epsg.shp'))

stereo_ids = list(query_footprint('pgc_imagery_catalogids_stereo', table=True, columns=['CATALOG_ID'])['catalog_id'])
master_sel['is_stereo'] = master_sel['catalog_id'].apply(lambda x: x in stereo_ids)

dems = query_footprint('pgc_dem_setsm_strips', table=True, columns=['catalogid1', 'catalogid2'])
dem_ids = list(dems['catalogid1']) + list(dems['catalogid2'])
master_sel['dem_exists'] = master_sel['catalog_id'].apply(lambda x: x in dem_ids)


akalb = {'init':'epsg:3338'}
master_sel = master_sel.to_crs(akalb)
master_sel.geometry = master_sel.geometry.buffer(5000)

bore = bore.to_crs(akalb)
if 'index_right' in list(bore):
    bore.drop(columns=['index_right'], inplace=True)

sj = gpd.sjoin(master_sel, bore, how='left')
counts = sj.groupby('Location').agg({'scene_id':'nunique', 'acq_time':['min','max']})
counts.to_excel(os.path.join(prj_dir, 'scene_summary.xlsx'))
stereo_counts = sj.groupby(['Location', 'is_stereo', 'dem_exists']).agg({'catalog_id':'nunique'})
stereo_counts.to_excel(os.path.join(prj_dir, 'catalog_id_stereo_summary.xlsx'))