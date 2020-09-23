from osgeo import gdal

def driver_support(driver_name):
	try:
	    driver = gdal.GetDriverByName(driver_name)
	    if driver:
	        print('{} driver found.'.format(driver_name))
	    else:
	        print('{} driver not found.'.format(driver_name))
	except Exception as e:
		print('Error locating {} driver.'.format(driver_name))
		print(e)

def test_bigtiff():
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

test_bigtiff()

drivers = ['OpenFileGDB', 'FileGDB', 'ESRI FileGDB']
for d in drivers:
    driver_support(d)

test_bigtiff()