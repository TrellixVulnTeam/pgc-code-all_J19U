# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 13:55:31 2019

@author: disbr007
"""


from osgeo import ogr, gdal
import os

from plotly.offline import plot
import plotly.graph_objs as go

## Project path
proj_p = r'E:\disbr07\scratch\plotly_dems'

## Load Shapefile to clip rasters and get extent
driver = ogr.GetDriverByName("ESRI Shapefile")
clip_p = r'E:\disbr007\scratch\plotly_dems\dem_aoi2.shp'
#clip_p = os.path.join(proj_p, 'dem_aoi.prj.shp')
ds = driver.Open(clip_p, 0)
lyr = ds.GetLayer()
ulx, lrx, lry, uly = lyr.GetExtent()
#ds = None


## Load rasters 
dems_plot = []
dem_p1 = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\trans\WV01_2016.tif'
dem_p2 = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\trans\WV01_2012.tif'
dem_p3 = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\trans\Diff_2016_2012.tif'
dems = [dem_p1, dem_p2, dem_p3]
for dem_p in dems:
        
    dem_ds = gdal.Open(dem_p)
    dem_op = r'E:\disbr007\scratch\plotly_dems\dem_2016.tif'
    # Clip to shapefile extent
    dem_ds = gdal.Translate(dem_op, dem_ds, projWin=[ulx, uly, lrx, lry])
    
    # Read as array
    dem_arr = dem_ds.ReadAsArray()
    dem_ds = None
    dems_plot.append(dem_arr)
    
#data = [go.Surface(z=dems_plot[0], colorscale='Blues', visible=False),
#        go.Surface(z=dems_plot[1], colorscale='Reds', visible=True)]
data = [go.Surface(z=dems_plot[2], showscale=False, opacity=1, colorscale='Hot')]
#dem1 = go.Surface(z=dems_plot[0], colorscale='Blues', visible=False, name='2016')
#dem2 = go.Surface(z=dems_plot[1], colorscale='Reds', visible=True, name='2012')
#
#data = [dem1, dem2]


updatemenus = list([
    dict(type="buttons",
         active=-1,
         buttons=list([   
            dict(label = '2016',
                 method = 'restyle',
                 args = [{'visible': [True, False]}]),
            dict(label = '2012',
                 method = 'restyle',
                 args = [{'visible': [False, True]}]),
        ]),
    )
])

layout = dict(updatemenus=updatemenus)
#fig = dict(data=data, layout=layout)

fig = go.Figure(data=data, layout=layout)
plot(data, auto_open=True)















