import arcpy
import os

mxd_path = r"C:\Users\disbr007\imagery\nga_maps\stereo_rates.mxd"
mxd = arcpy.mapping.MapDocument(mxd_path)

year_elem = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[1] # the element representing the date range

years = ['2016', '2017', '2018'] # years to create maps for

fp = arcpy.mapping.ListLayers(mxd)[1] # dg.stereo.cc20 layer

for i, year in enumerate(years):
	# set definition query to only desired dates
	sql = "acqdate > '{}-02-14'".format(year)
	print(sql)
	fp.definitionQuery = sql
	year_elem.text = '{} - 2019'.format(year) # change text to reflect definition query
	outpath = os.path.join(os.path.dirname(mxd_path), 'culm', 'culm_{}.png'.format(year))
	arcpy.mapping.ExportToPNG(mxd, outpath, resolution=150)