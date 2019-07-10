import os, string, sys, shutil, math, glob, re, argparse, logging, tqdm
import numpy as np
print("Importing arcpy...")
import arcpy
print("Imported arcpy")


#### Create Loggers
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)


def range_tuples(start, stop, step):
    '''
    Generates tuples for every pair of two steps in the given range.
    I.e.:
    start = 0
    stop = 3
    step = 1
    returns -> [(0,1), (1,2), (2,3)]
    '''    
    ranges = []
    lr = np.arange(start, stop+step, step)
    for i, r in enumerate(lr):
        if i < len(lr)-1:
            ranges.append((r, lr[i+1]))
            
    return ranges

    
def lat_lon_cells(lat_step, lon_step):
    '''
    Splits the entire range of latitudes and longitudees
    into cells with size lat_step by lon_step in degrees
    '''
    
    lats = range_tuples(-90, 90, lat_step)
    lons = range_tuples(-180, 180, lon_step)

    cells = []
    for min_lat, max_lat in lats:
        for min_lon, max_lon in lons:
            cells.append((min_lon, min_lat, max_lon, max_lat))
            
    return cells


def write_bbs(cells, out_path):
    '''
    takes a list of tuples of coordinates and writes them as a polygon
    cells: list of tuples of (min_lon, min_lat, max_lon, max_lat)
    '''

    try:
        from shapely.geometry import Point, Polygon, mapping
        import fiona
        from fiona.crs import from_epsg


        # Write shapefile
        schema = {'geometry': 'Polygon', 
                  'properties': {
                  'id': 'int', 
                  'corners': 'str', 
                  'top_right': 'str'}}

        crs = from_epsg(4326)
        driver = 'ESRI Shapefile'
        out_path = os.path.join(os.path.dirname(out_path), 'bb_test.shp')


        for cell in cells:
            min_lat, max_lat = cell[1], cell[3]
            min_lon, max_lon = cell[0], cell[2]
            
            # For attribute field to match feature class naming
            min_lat_name = str(min_lat).replace('-', 'neg')
            max_lat_name = str(max_lat).replace('-', 'neg')
            min_lon_name = str(min_lon).replace('-', 'neg')
            max_lon_name = str(max_lon).replace('-', 'neg')

            points = [Point(min_lon, min_lat), Point(min_lon, max_lat), Point(max_lon, max_lat), Point(max_lon, min_lat)]
            
            # Write four points as polygon geometry
            coords = [(p.x, p.y) for p in points]
            poly = Polygon(coords)
            
            try:
                with fiona.open(out_path, 'a', driver='ESRI Shapefile', schema=schema, crs=crs) as shp:
                    shp.write({
                        'geometry': mapping(poly),
                        'properties': {
                        'id': 1, 
                        'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon),
                        'top_right': 'LAT{}_LON{}'.format(max_lat_name, max_lon_name)}
                })
            except OSError:
                with fiona.open(out_path, 'w', driver='ESRI Shapefile', schema=schema, crs=crs) as shp:
                    shp.write({
                            'geometry': mapping(poly),
                            'properties': {
                            'id': 1, 
                            'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon), 
                            'top_right': 'LAT{}_LON{}'.format(max_lat_name, max_lon_name)}})
    except ImportError as e:
        logger.warning(e)
        logger.warning("Skipped writing bounding boxes due to missing modules.")


def main():

    #### Set Up Arguments
    parser = argparse.ArgumentParser(description="Slice master footprint into sub-regions.")

    parser.add_argument("mfp", help="master footprint gdb layer")
    parser.add_argument("lat_step", type=int, help="Latitude step")
    parser.add_argument("lon_step", type=int, help="Longitude step")
    parser.add_argument("-o", "--out_gdb", type=str,
        help="Path to output gdb. Can be existing or to be created")
    parser.add_argument("-b", "--bounding_box_only", action='store_true',
        help="Skip slicing master footprint and just write bounding box using given lat/lon steps.")

    #### Parse Arguments
    args = parser.parse_args()
    mfp = os.path.abspath(args.mfp)
    gdb,lyr = os.path.split(mfp)
    lat_step = args.lat_step
    lon_step = args.lon_step
    if args.out_gdb:
        out_gdb = os.path.abspath(args.out_gdb)



    #### Validate Required Arguments
    if not arcpy.Exists(mfp):
        parser.error("mfp path is not a valid dataset")


    #### Confirm write path, delete existing 
    if args.out_gdb:
        if arcpy.Exists(out_gdb):
            logging.info('''Existing GDB found at out path: {}\n
                This will result in an overwrite if reslicing master footprint with 
                the a previously used lat_step and lon_step.'''.format(out_gdb))
            overwrite = input('Do you wish to continue? [y/n] ')
            if str.lower(overwrite) == 'n':
                sys.exit()
        else:
            out_dir, out_name = os.path.split(out_gdb)
            logger.info('Creating GDB at {}'.format(os.path.join(out_dir, out_name)))
            out_gdb = arcpy.CreateFileGDB_management(out_dir, out_name)
    else:
        out_gdb = gdb


    # Set up logging.
    lsh = logging.StreamHandler()
    lsh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s- %(message)s', '%m-%d-%Y %H:%M:%S')
    lsh.setFormatter(formatter)
    # logger.addHandler(lsh)
    
    arcpy.env.workspace = out_gdb
    arcpy.env.overwriteOutput = True

    #### Derive subdatasets and P1BS versions
    # Datasets: source, dst, expression
    dss = []
    cells = lat_lon_cells(lat_step, lon_step)

    #### If not skip slicing
    if args.bounding_box_only == False:    
        for cell in cells:
            min_lat, max_lat = cell[1], cell[3]
            min_lon, max_lon = cell[0], cell[2]

            # For file naming
            min_lat_name = str(min_lat).replace('-', 'neg')
            max_lat_name = str(max_lat).replace('-', 'neg')
            min_lon_name = str(min_lon).replace('-', 'neg')
            max_lon_name = str(max_lon).replace('-', 'neg')
        
            # Add files to list to write
            dss.append((os.path.join(gdb, lyr), 
                '{}_LAT{}_LON{}'.format(lyr, max_lat_name, max_lon_name), 
                """CENT_LAT > {} AND CENT_LAT <= {} AND CENT_LONG > {} AND CENT_LONG <= {}""".format(min_lat, max_lat, min_lon, max_lon)))
        
        for ds in tqdm.tqdm(dss):
            src, dst, exp = ds
            # print('{}\n{}\n{}\n'.format(src, dst, exp))
            logger.info("Calculating {}".format(dst))
            arcpy.FeatureClassToFeatureClass_conversion(src,out_gdb,dst,exp)
            logger.info("Adding index to {}".format(dst))
            arcpy.AddIndex_management(os.path.join(out_gdb,dst),"CATALOG_ID","catid")
            logger.info("Created {}".format(dst))

    logger.info('Writing bounding boxes as shapefile.')
    logger.info(out_gdb)
    write_bbs(cells, out_gdb)

if __name__ == '__main__':
    main()
