# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 09:14:31 2019

@author: disbr007
arcpy mapping - zoom to features and export PNG
"""

import arcpy
print('arcpy imported successfully')

import copy
import os


def clear_selection(dfs, mxd):
	for df in dfs:
		for lyr in arcpy.mapping.ListLayers(mxd, '*', df):
			if lyr.isFeatureLayer:
				arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")
		for tbl in arcpy.mapping.ListTableViews(mxd, '*', df):
			arcpy.SelectLayerByAttribute_management(tbl, "CLEAR_SELECTION")


def iterate_views_export(layer, view_layer, fields, mxd, output_dir, resolution):
	'''
	Iterates through each feature in view_layer, zooms to it, and exports a PNG.
	'''
	print([f.name for f in arcpy.ListFields(view_layer)])
	with arcpy.da.SearchCursor(view_layer, ['FID', 'Name', 'projection']) as view_cursor:
		for row in view_cursor:
			## Select the the current rows view feature
			current_view = arcpy.SelectLayerByAttribute_management(view_layer, where_clause='FID = {}'.format(row[0]))
			df.zoomToSelectedFeatures()

			## Export
			out_name = '{}_{}_{}.png'.format(layer.name, view_layer.name, row[1])
			out_path = os.path.join(output_dir, out_name)
			arcpy.mapping.ExportToPNG(mxd, out_path, resolution=output_resolution)

	del view_cursor


#### GENERAL SETTINGS
prj_dir = r'C:\Users\disbr007\projects\coastline'
output_resolution = 75
output_dir = os.path.join(prj_dir, 'presentation', 'maps')


#### Get map document
mxd_path = r'coastline_density.mxd'
mxd = arcpy.mapping.MapDocument(os.path.join(prj_dir, mxd_path))


#### Get layers and dataframe
coastline_layers = arcpy.mapping.ListLayers(mxd, '*density*')
coastline_layers = [lyr for lyr in coastline_layers if 'intrack' not in lyr.name]
## Layer holding polygons to zoom to
view_layers = arcpy.mapping.ListLayers(mxd, '*views*')
global_view = [lyr for lyr in view_layers if lyr.name == 'views'][0]
arctic_view = [lyr for lyr in view_layers if 'arctic' in lyr.name][0]

## Get dataframe for use in zoomToSelectedFeatures
dfs = arcpy.mapping.ListDataFrames(mxd)
df = dfs[0]


#### Set up map document
arcpy.RefreshActiveView()  
arcpy.RefreshTOC()
## Turn views off
global_view.visible = False
arctic_view.visible = False


#### Titles and annotation
text = {
	'oh_density': {'title': 'On hand'},
	'dg_density': {'title': 'Archive'},
	'mfp_density': {'title': 'At PGC'},
	'nasa_density': {'title': 'At NASA'}
}


#### Iterate through density layers
for layer in coastline_layers:
	print('working on {}'.format(layer.name))
	print([lyr.name for lyr in coastline_layers])
	## Turn current layer on, all others off
	layer.visible = True
	other_layers = [lyr for lyr in coastline_layers if lyr.name != layer.name]
	# other_layers = [lyr for lyr in coastline_layers]
	# other_layers.remove(layer)
	for ol in other_layers:
		ol.visible = False

	#### Iterate through views
	## Clear selection
	clear_selection(dfs, mxd)

	iterate_views_export(layer=layer, view_layer=global_view, 
		fields=['FID', 'Name', 'projection'], 
		mxd=mxd, 
		output_dir=output_dir, 
		resolution=output_resolution)

	# with arcpy.da.SearchCursor(view_layer, ['FID', 'Name', 'projection']) as view_cursor:
	# 	for row in view_cursor:
	# 		## Select the the current rows view feature
	# 		current_view = arcpy.SelectLayerByAttribute_management(view_layer, where_clause='FID = {}'.format(row[0]))
	# 		df.zoomToSelectedFeatures()

	# 		## Export
	# 		out_name = '{}_{}.png'.format(layer.name, row[1])
	# 		out_path = os.path.join(output_dir, out_name)
	# 		arcpy.mapping.ExportToPNG(mxd, out_path, resolution=output_resolution)

	# del view_cursor


#### Print statements for testing
print(mxd.title)
# print([layer.name for layer in density_layers])

del mxd