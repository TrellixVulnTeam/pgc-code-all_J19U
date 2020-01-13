"""
Reproject a shapfile -- copied directly from ogr-cookbook, coverted to function
with in memory writing ability.
"""

import copy
import os
import logging
import posixpath

from osgeo import gdal, ogr, osr

from get_creds import get_creds


logger = logging.getLogger('gdal_tools')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


ogr.UseExceptions()
gdal.UseExceptions()


def ogr_reproject(input_shp, to_sr, output_shp=None, in_mem=False):
    """
    Reproject shapefile using OGR.
    ** in memory reprojection not currently working /vsimem/**
    ** only works for polygons --> output geom_type needs to be fixed **
    """
    driver = auto_detect_ogr_driver(input_shp)
    
    # TODO: Improve the logic around in Memory Layers (not functional)
    if driver.GetName() == 'Memory':
        input_shp_name = 'mem_lyr'
        in_mem = True
        # If driver is Memory assume an ogr.DataSource is being passed
        # as input_shp
        inLayer = input_shp.GetLayer(0)
    else:
        # Get the input layer
        # Get names of from input shapefile path for output shape
        input_shp_name = os.path.basename(input_shp)
        input_shp_dir = os.path.dirname(input_shp)
        inDataSet = driver.Open(input_shp)
        inLayer = inDataSet.GetLayer(0)
    
    # Get the source spatial reference
    inSpatialRef = inLayer.GetSpatialRef()

    # create the CoordinateTransformation
    coordTrans = osr.CoordinateTransformation(inSpatialRef, to_sr)


    # Create the output layer
    # Default output shapefile name and location -- same as input
    if output_shp is None and in_mem is False:
        # TODO: Fix this
        output_shp = os.path.join(input_shp_dir, input_shp_name)
    # In memory output
    elif in_mem is True:
        output_shp = os.path.join('/vsimem', 'mem_lyr.shp'.format(input_shp_name))
        # Convert windows path to unix path (required for gdal in-memory)
        output_shp = output_shp.replace(os.sep, posixpath.sep)

    # Check if output exists
    if os.path.exists(output_shp):
        remove_shp(output_shp)
        # driver.DeleteDataSource(output_shp)
    if in_mem is True:
        outDataSet = driver.CreateDataSource(os.path.basename(output_shp).split('.')[0])
    else:
        outDataSet = driver.CreateDataSource(os.path.dirname(output_shp))
        # outDataSet = driver.CreateDataSource(output_shp)
    # TODO: Support non-polygon input types
    # TODO: Fix this -- creating names like test.shp.shp
    output_shp_name = os.path.basename(output_shp).split('.')[0]
    outLayer = outDataSet.CreateLayer(output_shp_name, geom_type=ogr.wkbMultiPolygon)

    # Add fields
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    # Get the output layer's feature definition
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

    if in_mem is False:
        # Create .prj file
        outdir = os.path.dirname(output_shp)
        outname = os.path.basename(output_shp).split('.')[0]
        out_prj = os.path.join(outdir, '{}.prj'.format(outname))
        to_sr.MorphToESRI()
    
        file = open(out_prj, 'w')
        file.write(to_sr.ExportToWkt())
        file.close()

    # Save and close the shapefiles
    inLayer = None
    inDataSet = None
    outLayer = None
    outDataSet = None
        
    return output_shp


def get_shp_sr(in_shp):
    """
    Get the crs of in_shp.
    in_shp: path to shapefile
    """
    driver = auto_detect_ogr_driver(in_shp)
    if driver.GetName() == 'Memory':
        lyr = in_shp.GetLayer()
    else:
        ds = driver.Open(in_shp)
        lyr = ds.GetLayer()
    srs = lyr.GetSpatialRef()
    lyr = None
    ds = None
    return srs


def get_raster_sr(raster):
    """
    Get the crs of raster.
    raster: path to raster.
    """
    ds = gdal.Open(raster)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(wkt=prj)
    prj = None
    ds = None
    return srs


def check_sr(shp_p, raster_p):
    """
    Check that spatial reference of shp and raster are the same.
    Optionally reproject in memory.
    """
     # Check for common spatial reference between shapefile and first raster
    shp_sr = get_shp_sr(shp_p)
    raster_sr = get_raster_sr(raster_p)
    
    if shp_sr != raster_sr:
        sr_match = False
        logger.debug('''Spatial references do not match...''') 
        logger.debug('Shape SR: \n{} \nRaster SR:\n{}'.format(shp_sr, raster_sr))
    else:
        sr_match = True

    return sr_match


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


def auto_detect_ogr_driver(ogr_ds):
    """
    Autodetect the appropriate driver for an OGR datasource.
    

    Parameters
    ----------
    ogr_ds : OGR datasource
        Path to OGR datasource.

    Returns
    -------
    OGR driver.
    """
    # OGR driver lookup table
    driver_lut = {'json': 'GeoJSON',
                  'shp' : 'ESRI Shapefile',
                  # TODO: Add more
                  }
    
    # Check if in-memory datasource
    if isinstance(ogr_ds, ogr.DataSource):
        driver_name = 'Memory'
    elif 'vsimem' in ogr_ds:
        driver_name = 'Memory'
    else:
        # Check if extension in look up table
        try:
            ext = os.path.basename(ogr_ds).split('.')[1]
            if ext in driver_lut.keys():
                driver_name = driver_lut[ext]
            else:
                logger.info("""Unsupported driver extension {}
                                Defaulting to 'ESRI Shapefile'""".format(ext))
                driver_name = driver_lut['shp']
        except:
            logger.info('Unable to locate OGR driver for {}'.format(ogr_ds))
            driver_name = None
    
    try:
        driver = ogr.GetDriverByName(driver_name)
    except ValueError as e:
       print('ValueError with driver_name: {}'.format(driver_name))
       print('OGR DS: {}'.format(ogr_ds))
       raise e
    return driver


def remove_shp(shp):
    """
    Remove the passed shp path and all meta-data files.
    ogr.Driver.DeleteDataSource() was not removing 
    meta-data files.
    
    Parameters
    ----------
    shp : os.path.abspath
        Path to shapefile to remove
    
    Returns
    ----------
    None
    
    """
    if os.path.exists(shp):
        logger.debug('Removing shp: {}'.format(shp))
        for ext in ['prj', 'dbf', 'shx', 'cpg', 'sbn', 'sbx']:
            meta_file = shp.replace('shp', ext)
            if os.path.exists(meta_file):
                logger.debug('Removing metadata file: {}'.format(meta_file))
                os.remove(meta_file)
        os.remove(shp)
