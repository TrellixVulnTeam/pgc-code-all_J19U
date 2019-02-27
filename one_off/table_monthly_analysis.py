# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 15:46:01 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
import os

tbl_path = r"E:\disbr007\UserServicesRequests\Projects\1495_wlostowksi\3655\project_files\aoi_sel_MS.dbf"

tbl = gpd.read_file(tbl_path)
tbl_fields = ['STRIP_ID', 'SCENE_ID', 'SENSOR', 'CATALOG_ID', 'PROD_CODE', 'SPEC_TYPE', 'ACQ_TIME', 'CLOUDCOVER', 'BANDS', 'OFF_NADIR', 'SUN_ELEV']
tbl = tbl[tbl_fields]
tbl['ACQ_TIME'] = pd.to_datetime(tbl['ACQ_TIME'])
tbl.set_index('ACQ_TIME', inplace=True)

tbl_monthly = tbl.groupby([pd.Grouper(freq='M')]).agg({'SCENE_ID': 'nunique'})
tbl_monthly = tbl_monthly[(tbl_monthly.SCENE_ID != 0)]
tbl_monthly.reset_index(inplace=True)
tbl_monthly['ACQ_DATE'] = tbl_monthly.ACQ_TIME.apply(lambda x: str(x)[:7])

tbl_yr = tbl.groupby([pd.Grouper(freq='Y')]).agg({'SCENE_ID': 'nunique'})

out_path = os.path.join(os.path.dirname(tbl_path), 'monthly_summary.xlsx')
tbl_monthly.to_excel(out_path, 'Sheet1')