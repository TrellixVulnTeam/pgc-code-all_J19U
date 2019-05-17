import arcpy
import os
print('imported arcpy')

mxd_path = r"E:\disbr007\imagery_archive_analysis\cloudcover\cc_basemanp.mxd"
mxd = arcpy.mapping.MapDocument(mxd_path)

cc_elem = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0] # the element representing the cc

start = 20
stop = 50
step = 5
cc = [x for x in range(start, stop+step, step)] # cc to create maps for

fp = arcpy.mapping.ListLayers(mxd)[2] # dg.stereo.cc20 layer

for i, c in enumerate(cc):
	# set definition query to only desired cc
	sql = "cloudcover > 20 and cloudcover <= {}".format(c)
	print(sql)
	fp.definitionQuery = sql
	cc_elem.text = 'Cloud cover: 20 - {}%'.format(c) # change text to reflect definition query
	outpath = os.path.join(os.path.dirname(mxd_path), 'cc20_50', '20_{}.png'.format(c))
	arcpy.mapping.ExportToPNG(mxd, outpath, resolution=150)