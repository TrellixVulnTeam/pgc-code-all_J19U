"""Iterate through yeras in a footprint and export PNG"""

import os

import arcpy
print('Imported arcpy.')


mxd_p = r'E:\disbr007\imagery_archive_analysis\arctic_stereo_rate_2019oct08\project_basemap.mxd'
out_dir = r'E:\disbr007\imagery_archive_analysis\arctic_stereo_rate_2019oct08'

mxd = arcpy.mapping.MapDocument(mxd_p)

# Get element with text indicating year
year_elem = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0]

# Get dataframes
# dfs = arcpy.mapping.ListDataFrames(mxd)
# for df in dfs:
#	print(df.name)


# Get fp layer
lyrs = arcpy.mapping.ListLayers(mxd)
fp = [lyr for lyr in lyrs if lyr.name == 'arctic_stereo2019oct10'][0]


# Iterate years
date_range = range(2000, 2020)
for year in date_range:
	# Def. query sql
	sql = "acqdate LIKE '{}%'".format(year)
	fp.definitionQuery = sql

	# Update text
	text = 'Stereo Collection {}'.format(year)
	year_elem.text = text

	out_PNG = os.path.join(out_dir, 'arctic_stereo_archive_{}.png'.format(year))
	arcpy.mapping.ExportToPNG(mxd, out_PNG, resolution=500)
	print('Out image created at {}'.format(out_PNG))

sql = ""
fp.definitionQuery = sql
text = 'Stereo Archive'
year_elem.text = text
out_PNG = os.path.join(out_dir, 'arctic_stereo_archive.png')
arcpy.mapping.ExportToPNG(mxd, out_PNG, resolution=500)
print('Out image created at {}'.format(out_PNG))
