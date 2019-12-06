# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 13:55:43 2019

@author: disbr007
"""

import os
import geopandas as gpd
from osgeo import ogr

kmz_p = r'E:\disbr007\UserServicesRequests\Projects\bjones\1653\baldwin_IK01_QB02.kmz'


driver = ogr.GetDriverByName('LIBKML')

kmz_source = driver.Open(kmz_p, 0) # 0 means read-only. 1 means writeable.
kmz_layer  = kmz_source.GetLayer()
lyr_defn   = kmz_layer.GetLayerDefn()

for i in range(lyr_defn.GetFieldCount()):
    print(i)
    print(lyr_defn.GetFieldDefn(i).GetName())




catids = []
for feature in kmz_layer:
    desc = feature.GetField('description')
    brk = '<td>image_identifier</td>'
    catid = desc.split(brk)[1].split('<td>')[1].split('</td>')[0]
    print(catid)




out_shp = r'E:\disbr007\UserServicesRequests\Projects\bjones\1653\baldwin_IK01_QB02.kmz'
out_drv = 'ESRI Shapefile'



