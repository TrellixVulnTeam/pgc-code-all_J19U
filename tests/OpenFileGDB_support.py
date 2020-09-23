from osgeo import gdal


def open_file_gdb_support():
	try:
	    driver = gdal.GetDriverByName('OpenFileGDB')
	    if driver:
	        print('OpenFileGDB driver found.')
	    else:
	        print('OpenFileGDB driver not found.')
	except Exception as e:
		print('Error locating OpenFileGDB driver.')
		print(e)

open_file_gdb_support()
