from osgeo import gdal

md = gdal.GetDriverByName('GTiff').GetMetadata()
try:
	test = md['DMD_CREATIONOPTIONLIST'].find('BigTIFF')
	if test != -1:
		print('Success: {}'.format(test))
	else:
		print('Failure: {}'.format(test))
except Exception as e:
	print('BigTIFF Unsupported')
	print(e)