
print('testing gdal import...')
try:
	from osgeo import gdal
except Exception as e:
	print('Could not import gdal.')
	print(e)
	raise(e)
print('gdal imported successfully...')


print('testing bigtiff support...')
from tests.bigtiff_support import test_bigtiff
test_bigtiff()