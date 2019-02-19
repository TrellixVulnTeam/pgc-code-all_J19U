import arcpy
import os

mxd_path = r"C:\Users\disbr007\imagery\nga_maps\stereo_rates.mxd"
mxd = arcpy.mapping.MapDocument(mxd_path)

year_elem = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[1] # the element representing the date range

years = [x for x in range(2000, 2020, 1)] # years to create maps for

fp = arcpy.mapping.ListLayers(mxd)[1] # dg.stereo.cc20 layer

for i, year in enumerate(years):
	# ensure loop stays in range
	length = len(years)-1
	if i < length:
		# set definition query to only desired dates
		sql = "acqdate > '{}-00-00' AND acqdate < '{}-00-00'".format(year, years[i+1])
		print(sql)
		fp.definitionQuery = sql
		year_elem.text = '{}'.format(year) # change text to reflect definition query
		outpath = os.path.join(os.path.dirname(mxd_path), 'yearly', '{}.png'.format(year))
		arcpy.mapping.ExportToPNG(mxd, outpath, resolution=150)

mxd.save()