import os, string, sys, shutil, math, glob, re, argparse, logging, tqdm
print("Importing arcpy...")
import arcpy
print("Imported arcpy")

#### Create Loggers
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)


"""def range_tuples(start, stop, step):
    '''
    Generates tuples for every two steps in the given range
    '''    
    ranges = []
    lr = range(start, stop+step, step)
    for i, r in enumerate(lr):
        if i < len(lr)-1:
            ranges.append((r, lr[i+1]))
            
    return ranges
"""
    
# def lat_lon_cells(lat_step, lon_step):
#     '''
#     Splits the globe into cells with size lat_step x lon_step
#     '''
    
#     lats = range_tuples(-90, 90, lat_step)
#     lons = range_tuples(-180, 180, lon_step)

#     cells = []
#     for min_lat, max_lat in lats:
#         for min_lon, max_lon in lons:
#             cells.append((min_lon, min_lat, max_lon, max_lat))
            
#     return cells


# def write_bbs(cells):
#     '''
#     takes a list of tuples of coordinates and writes them as a polygon
#     cells: list of tuples of (min_lon, min_lat, max_lon, max_lat)
#     '''
#     try:
#         from shapely.geometry import Point, Polygon, mapping
#         import fiona
#         from fiona.crs import from_epsg
#         for cell in cells:
#             min_lat, max_lat = cell[1], cell[3]
#             min_lon, max_lon = cell[0], cell[2]
            
#             points = [Point(min_lon, min_lat), Point(min_lon, max_lat), Point(max_lon, max_lat), Point(max_lon, min_lat)]
            
#             # Write four points as polygon geometry
#             coords = [(p.x, p.y) for p in points]
#             poly = Polygon(coords)
            
#             # Write shapefile
#             schema = {'geometry': 'Polygon', 
#                       'properties': {'id': 'int', 'corners': 'str'}}
#             crs = from_epsg(4326)
#             driver = 'ESRI Shapefile'
#             out_path = r'C:\temp\mfp_slice_bb.shp'
#             if os.path.exists(out_path):
#                 os.remove(out_path)
#             try:
#                 with fiona.open(out_path, 'a', driver=driver, schema=schema, crs=crs) as shp:
#                     shp.write({
#                         'geometry': mapping(poly),
#                         'properties': {'id': 1, 'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon)}
#                 })
#             except OSError:
#                 with fiona.open(out_path, 'w', driver=driver, schema=schema, crs=crs) as shp:
#                     shp.write({
#                             'geometry': mapping(poly),
#                             'properties': {'id': 1, 'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon)},
#                     })
#     except ImportError as e:
#         print(e)
#         print("Skipped writing bounding boxes due to missing modules.")


def main():

    #### Set Up Arguments
    parser = argparse.ArgumentParser(description="slice mfp into sub-regions")

    parser.add_argument("mfp", help="master footprint gdb layer")
    parser.add_argument("--dryrun", action="store_true", default=False,
                    help="print actions without executing")

    #### Parse Arguments
    args = parser.parse_args()
    mfp = os.path.abspath(args.mfp)
    gdb,lyr = os.path.split(mfp)

    #### Validate Required Arguments
    if not arcpy.Exists(mfp):
        parser.error("mfp path is not a valid dataset")
    
    # Set up logging.
    lsh = logging.StreamHandler()
    lsh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s- %(message)s', '%m-%d-%Y %H:%M:%S')
    lsh.setFormatter(formatter)
    logger.addHandler(lsh)
    
    arcpy.env.workspace = gdb
    
    #### Derive subdatasets and P1BS versions
    # Datasets: source, dst, expression
    dss = []
    # lats = list(range(-90-lat_step, 90+lat_step, lat_step))
    lats = list(range(-95, 95, 5))

    for i, lat in enumerate(lats[1:-1]):
    # for cell in cells:
        min_lat = lats[i]
        max_lat = lats[i+1]
        min_lat_name = str(min_lat).replace('-', 'neg')
        max_lat_name = str(max_lat).replace('-', 'neg')
        dss.append((lyr, 
            '{}_{}_{}'.format(lyr, min_lat_name, max_lat_name), 
            """CENT_LAT > {} AND CENT_LAT <= {}""".format(min_lat, max_lat)))
    
    for ds in tqdm.tqdm(dss):
        src, dst, exp = ds
        logger.info("Calculating {}".format(dst))
        arcpy.FeatureClassToFeatureClass_conversion(src,gdb,dst,exp)
        logger.info("Adding index to {}".format(dst))
        arcpy.AddIndex_management(dst,"CATALOG_ID","catid")
        logger.info("Created {}".format(dst))
    

if __name__ == '__main__':
    main()

# dss = []
# lats = list(range(-100, 140, 20))
# for i, lat in enumerate(lats[1:-1]):
#     min_lat = lats[i]
#     min_lat_name = str(min_lat).replace('-', 'neg')
#     max_lat = lats[i+1]
#     max_lat_name = str(max_lat).replace('-', 'neg')
#     dss.append((lyr, '{}_{}_{}'.format(lyr, min_lat_name, max_lat_name), """CENT_LAT > {} AND CENT_LAT <= {}""".format(min_lat, max_lat)))