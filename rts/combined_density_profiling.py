# -*- coding: utf-8 -*-
"""
Created on Tue May 12 15:09:00 2020

@author: disbr007
"""

from dem_utils.dem_utils import combined_density
from misc_utils.logging_utils import create_logger

sublog = create_logger('dem_utils.dem_utils', 'sh', 'DEBUG')

mt1 = r'V:\pgc\data\scratch\jeff\ms\2020apr30\dems\raw\WV02_20120729_103001001A29A200_103001001B348300\WV02_20120729_103001001A29A200_103001001B348300_seg1_2m_matchtag.tif'
mt2 = r'V:\pgc\data\scratch\jeff\ms\2020apr30\dems\raw\W2W2_20100720_103001000677DF00_1030010006ACB500\W2W2_20100720_103001000677DF00_1030010006ACB500_seg2_2m_matchtag.tif'
aoi = r'V:\pgc\data\scratch\jeff\ms\2020apr30\aois\aoi1.shp'

cd = combined_density(mt1, mt2, aoi, clip=True)