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


def iterate_views_export(df, layer, view_layer, fields, mxd, output_dir, resolution):
	'''
	Iterates through each feature in view_layer, zooms to it, and exports a PNG.
	'''
	with arcpy.da.SearchCursor(view_layer, fields) as view_cursor:
		for row in view_cursor:
			### Select the the current rows view feature
			current_view = arcpy.SelectLayerByAttribute_management(view_layer, where_clause='FID = {}'.format(row[0]))

			### Set projection of dataframe
			## Get rows projection column
			# Projection field index
			prj_idx = [i for i, f in enumerate(fields) if f == 'projection'][0]
			prj = row[prj_idx]
			# Determine if string (path) or int (WKID)
			if len(prj) > 10:
				prj = row[prj_idx]
			else:
				prj = int(row[prj_idx])
			sr = arcpy.SpatialReference(prj)
			df.spatialReference = sr

			### Zoom to each 'view' feature
			df.zoomToSelectedFeatures()

			## Export
			ext = 'png'
			out_name = '{}_{}_{}_{}.{}'.format(layer.name, view_layer.name, df.spatialReference.name, row[1], ext)
			print(out_name)
			out_path = os.path.join(output_dir, out_name)
			created = os.listdir(output_dir)
			if out_name in created:
				print('pass')
				pass
			else:
				arcpy.mapping.ExportToPNG(mxd, out_path, resolution=output_resolution)
				# arcpy.mapping.ExportToTIFF(mxd, out_path, resolution=output_resolution)
				# arcpy.mapping.ExportToPDF(mxd, out_path, resolution=output_resolution, image_quality='BEST', image_compression='NONE')
	del view_cursor


#### GENERAL SETTINGS
prj_dir = r'C:\Users\disbr007\projects\coastline'
output_resolution = 400
output_dir = os.path.join(prj_dir, 'presentation', 'maps')


#### Get map document
mxd_path = r'coastline_density.mxd'
mxd = arcpy.mapping.MapDocument(os.path.join(prj_dir, mxd_path))

#### Get layers and dataframe
coastline_layers = arcpy.mapping.ListLayers(mxd, '*density*')
coastline_layers = [lyr for lyr in coastline_layers if 'intrack' not in lyr.name]
archive_layers = arcpy.mapping.ListLayers(mxd, '*intrack*')

coast = arcpy.mapping.ListLayers(mxd, '*_pline*')[0]

## Layer holding polygons to zoom to
view_layers = arcpy.mapping.ListLayers(mxd, '*views*')
global_view = [lyr for lyr in view_layers if lyr.name == 'views'][0]
arctic_view = [lyr for lyr in view_layers if 'arctic' in lyr.name][0]
ian_view = [lyr for lyr in view_layers if 'ian' in lyr.name][0]
## Turn views off
global_view.visible = False
arctic_view.visible = False

## Get dataframe for use in zoomToSelectedFeatures
dfs = arcpy.mapping.ListDataFrames(mxd)
df = dfs[0]


#### Set up map document
arcpy.RefreshActiveView()  
arcpy.RefreshTOC()


#### Titles and annotation
text = {
	'oh_density': {'title': 'On hand'},
	'dg_density': {'title': 'Archive'},
	'mfp_density': {'title': 'At PGC'},
	'nasa_density': {'title': 'At NASA'}
}

fields = ['FID', 'Name', 'projection']
#### Iterate through density layers
for layer in coastline_layers:
	print('working on {}'.format(layer.name))
	## Turn current layer on, all others off
	layer.visible = True
	other_layers = [lyr for lyr in coastline_layers if lyr.name != layer.name]
	# print('turning off: {}'.format(other_layers))
	for ol in other_layers:
		ol.visible = False

	#### Iterate through views

	texts = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")
	source = [t for t in texts if t.name == 'source'][0]
	source.text = '<BOL>{}</BOL>'.format(text[layer.name]['title'])
	text_positionX = source.elementPositionX
	text_positionY = source.elementPositionY
	## Iterate global views
	## Clear selection
	clear_selection(dfs, mxd)
	iterate_views_export(df=df, layer=layer, view_layer=global_view, fields=fields, mxd=mxd, output_dir=output_dir, resolution=output_resolution)

	## Iterate artic views 
	clear_selection(dfs, mxd)
	iterate_views_export(df=df, layer=layer, view_layer=arctic_view, fields=fields, mxd=mxd, output_dir=output_dir, resolution=output_resolution)
	layer.visible = False

#### Ians views
iv = {
	'global': 'global_density_intrackcc20',
	'arctic': 'arctic_density_intrackcc20',
	'nam': 'NAm_density_intrackcc20',
	'ak': 'ak_density_intrackcc20',
}

for layer in archive_layers:
	print('working on {}'.format(layer.name))
	layer.visible = True
	other_layers = [lyr for lyr in archive_layers if lyr.name != layer.name]
	for ol in other_layers:
		ol.visible = False

	#### Iterate through views
	#### Move text off page - not needed
	texts = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")
	source = [t for t in texts if t.name == 'source'][0]
	# source.text = '<BOL>{}</BOL>'.format(text[layer.name]['title'])
	source.elementPositionX = 0.0
	source.elementPositionY = 10.0
	clear_selection(dfs, mxd)

	with arcpy.da.SearchCursor(ian_view, fields) as view_cursor:
		for row in view_cursor:
			### Select the the current rows view feature
			current_view = arcpy.SelectLayerByAttribute_management(ian_view, where_clause='FID = {}'.format(row[0]))

			name_idx = [i for i, fld in enumerate(fields) if fld == 'Name'][0]
			view_name = row[name_idx]

			if layer.name == iv[view_name]:
				### Set projection of dataframe
				## Get rows projection column
				# Projection field index
				prj_idx = [i for i, f in enumerate(fields) if f == 'projection'][0]
				prj = row[prj_idx]

				# Determine if string (path) or int (WKID)
				if len(prj) > 10:
					prj = row[prj_idx]
				else:
					prj = int(row[prj_idx])
				sr = arcpy.SpatialReference(prj)
				df.spatialReference = sr

				### Zoom to each 'view' feature
				df.zoomToSelectedFeatures()

				## Export
				ext = 'png'
				out_name = '{}_{}_{}_{}.{}'.format(layer.name, ian_view, df.spatialReference.name, row[1], ext)
				print(out_name)
				out_path = os.path.join(output_dir, out_name)
				created = os.listdir(output_dir)
				if out_name in created:
					print('pass')
					pass
				else:
					arcpy.mapping.ExportToPNG(mxd, out_path, resolution=output_resolution)
					# arcpy.mapping.ExportToTIFF(mxd, out_path, resolution=output_resolution)
					# arcpy.mapping.ExportToPDF(mxd, out_path, resolution=output_resolution, image_quality='BEST', image_compression='NONE')
	del view_cursor

	layer.visible = False

#### Move text back to it's original position
source.elementPositionX = text_positionX
source.elementPositionY = text_positionY

# #### Print statements for testing
# # print(mxd.title)
# # print([layer.name for layer in density_layers])

del mxd