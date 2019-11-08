"""
Reproject a shapfile -- copied directly from ogr-cookbook, coverted to function
with in memory writing ability.
"""

import os
import posixpath

from osgeo import gdal, ogr, osr

from get_creds import get_creds


ogr.UseExceptions()
gdal.UseExceptions()


def ogr_reproject(input_shp, to_sr, output_shp=None, in_mem=False):
	"""
	Reproject shapefile using OGR.
	** in memory reprojection not currently working /vsimem/**
	** only works for polygons --> output geom_type needs to be fixed **
	"""
	# Get names of from input shapefile path for output shape
	input_shp_name = os.path.basename(input_shp).split('.')[0]
	input_shp_dir = os.path.dirname(input_shp)
	# Default output shapefile name and location
	if output_shp is None and in_mem is False:
		output_shp_name = r'{}_prj.shp'.format(input_shp_name)
		output_shp = os.path.join(input_shp_dir, output_shp_name)
	# In memory output
	if output_shp is None and in_mem is True:
		output_shp = os.path.join('vsimem', '{}_prj'.format(input_shp_name))
		# Convert windows path to unix path (required for gdal in-memory)
		output_shp = output_shp.replace(os.sep, posixpath.sep)

	driver = ogr.GetDriverByName('ESRI Shapefile')  # autodetect driver???

	# output SpatialReference
	outSpatialRef = to_sr

	# get the input layer
	inDataSet = driver.Open(input_shp)
	inLayer = inDataSet.GetLayer()
	inSpatialRef = inLayer.GetSpatialRef()

	# create the CoordinateTransformation
	coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

	# create the output layer
	outputShapefile = output_shp
	if os.path.exists(outputShapefile):
	    driver.DeleteDataSource(outputShapefile)
	outDataSet = driver.CreateDataSource(outputShapefile)
	outLayer = outDataSet.CreateLayer(output_shp, geom_type=ogr.wkbMultiPolygon)

	# add fields
	inLayerDefn = inLayer.GetLayerDefn()
	for i in range(0, inLayerDefn.GetFieldCount()):
	    fieldDefn = inLayerDefn.GetFieldDefn(i)
	    outLayer.CreateField(fieldDefn)

	# get the output layer's feature definition
	outLayerDefn = outLayer.GetLayerDefn()

	# loop through the input features
	inFeature = inLayer.GetNextFeature()
	while inFeature:
	    # get the input geometry
	    geom = inFeature.GetGeometryRef()
	    # reproject the geometry
	    geom.Transform(coordTrans)
	    # create a new feature
	    outFeature = ogr.Feature(outLayerDefn)
	    # set the geometry and attribute
	    outFeature.SetGeometry(geom)
	    for i in range(0, outLayerDefn.GetFieldCount()):
	        outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
	    # add the feature to the shapefile
	    outLayer.CreateFeature(outFeature)
	    # dereference the features and get the next input feature
	    outFeature = None
	    inFeature = inLayer.GetNextFeature()

	# Save and close the shapefiles
	inDataSet = None
	outDataSet = None

	# Create .prj file
	outdir = os.path.dirname(output_shp)
	outname = os.path.basename(output_shp).split('.')[0]
	out_prj = os.path.join(outdir, '{}.prj'.format(outname))
	if in_mem is True:
		# Convert to unix style path as req. by gdal in-memory driver
		out_prj = out_prj.replace(os.sep, posixpath.sep)
	outSpatialRef.MorphToESRI()

	file = open(out_prj, 'w')
	file.write(outSpatialRef.ExportToWkt())
	file.close()

	return output_shp


def get_shp_sr(in_shp):
    """
    Get the crs of in_shp.
    in_shp: path to shapefile
    """
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.Open(in_shp)
    lyr = ds.GetLayer()
    srs = lyr.GetSpatialRef()

    return srs


def get_raster_sr(raster):
    """
    Get the crs of raster.
    raster: path to raster.
    """
    ds = gdal.Open(raster)
    prj = ds.GetProjection()
    print(prj)
    print('\n\n')
    srs = osr.SpatialReference(wkt=prj)

    return srs


def load_danco_table(db_name, db_tbl, where='1=1', load_fields=['*'], username=get_creds()[0], password=get_creds()[1]):
	"""
	Load a table from danco.pgc.umn.edu. The reference to the connection datasource
	must be return or the Layer becomes NULL.
	db_name    :    str    name of database holding table    'footprint', 'imagery', 'etc'
	db_tbl     :    str    name of database table to load    'sde.usgs_index_aerial_image_archive'
	where      :    str    WHERE portion of SQL statement    '{db_tbl}.{field} IN ('val1', 'val2')
	load_fields:    list   fields in db_tbl to load          ['field1', 'field2']
	username   :    str    username for connecting danco
	password   :    str    password for connecting danco

	returns osgeo.ogr.Layer, osgeo.ogr.DataSource
	"""
	db_server = 'danco.pgc.umn.edu'
	conn_str = "PG: host={} dbname={} user={} password={}".format(db_server, db_name, username, password)

	conn = ogr.Open(conn_str)

	load_fields = str(load_fields)[1:-1].replace("'", "")

	sql = """SELECT {} FROM {} WHERE {}""".format(load_fields, db_tbl, where)
	print('{}...'.format(sql[0:100]))

	lyr = conn.ExecuteSQL(sql)

	# TODO: Remove this after testing
	print('SQL selection: {}'.format(lyr.GetFeatureCount()))

	return lyr, conn
