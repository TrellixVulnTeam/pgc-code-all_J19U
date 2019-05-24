# -*- coding: utf-8 -*-
"""
Created on Wed May 22 13:23:52 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os


driver = 'ESRI_Shapefile'

## Paths
# path to imagery subset
sel_path = r'E:\disbr007\imagery_archive_analysis\cloudcover\dg_archive_dg_archive_stereo_cc21_30.shp'
# paths to aois to select by
aois_path = r'E:\disbr007\general' # aoi's live here
conus_path = os.path.join(aois_path, 'CONUS.shp')
baltics_path = os.path.join(aois_path, 'Baltics.shp')
so_russ_path = os.path.join(aois_path, 'russia_southern.shp')


## Load data
sel = gpd.read_file(sel_path, driver='ESRI Shapefile')
conus = gpd.read_file(conus_path, driver=driver)
baltics = gpd.read_file(baltics_path, driver=driver)
so_russ = gpd.read_file(so_russ_path, driver=driver)


## Merge relevant AOIs 
#improve to support any table format, just on geometry and name cols, currently all from CountriesWGS84
aoi = pd.concat([conus,baltics,so_russ])


## Determine if image in aoi
# Use centroid
sel['centroid'] = sel.centroid
sel.set_geometry('centroid', inplace=True)

# Determine if each centroid is in the aoi
sel = gpd.sjoin(sel, aoi, how='left') # returns NaN if no match
#sel['test'] = sel.within(aoi).reset_index(drop=True)
sel['aoi'] = sel.CNTRY_NAME.notnull().astype(int)

# Convert back to footprint geometry
sel.set_geometry('geometry', inplace=True)
sel.drop('centroid', axis=1, inplace=True)

#sel.to_file(os.path.join(os.path.dirname(sel_path), 'intersect.shp'))

in_aoi = sel[sel.aoi == 1]
not_aoi = sel[sel.aoi == 0]

in_aoi.to_file("E:\disbr007\imagery_orders\PGC_order_2019may21_stereo_cc21_30_conus_baltics_sorussia\stereo_cc21_30_conus_baltics_sorussia.shp")
not_aoi.to_file("E:\disbr007\imagery_orders\PGC_order_2019may21_stereo_cc21_30_not_conus_baltics_sorussia\stereo_cc21_30_not_conus_baltics_sorussia.shp")