from osgeo import gdal


def open_file_gdb_support():
	try:
	    driver = gdal.GetDriverByName('OpenFileGDB')
	    if driver:
	        print('OpenFileGDB driver found.')
	    else:
	        print('OpenFileGDB driver not found.')

open_file_gdb_support()
