# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:01:16 2019

@author: disbr007
"""

import os
import geopandas as gpd
from dataframe_utils import create_month_col, convert_datetime_to_string

sel_path = r'E:\disbr007\UserServicesRequests\Projects\_nnunez\project_files\aoi_prj_ovlp.shp'
sel = gpd.read_file(sel_path, driver='ESRI Shapefile')
sel = sel[sel.CLOUDCOVER <= .20]


create_month_col(sel, 'ACQ_TIME')
sel = sel[(sel.ACQ_TIME > '2009') & (sel.ACQ_TIME < '2017-08-16') & sel.Month.isin([7, 8])]
sel = sel.drop(columns=['Month'])
convert_datetime_to_string(sel)

sel.to_file(os.path.join(os.path.dirname(sel_path), '2019may22_nnunez_greenland_imagery.shp'))
