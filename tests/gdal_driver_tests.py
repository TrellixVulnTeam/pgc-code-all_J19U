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

drivers = ['OpenFileGDB', 'FileGDB', 'ESRI FileGDB']
for d in drivers:
    driver_support(d)