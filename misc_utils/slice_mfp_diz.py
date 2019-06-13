import os, string, sys, shutil, math, glob, re, argparse, logging, tqdm
print("Importing arcpy...")
import arcpy
print("Imported arcpy")

#### Create Loggers
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)

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
    lats = list(range(-95, 100, 5))
    for i, lat in enumerate(lats[1:-1]):
        min_lat = lats[i]
        min_lat_name = str(min_lat).replace('-', 'neg')
        max_lat = lats[i+1]
        max_lat_name = str(max_lat).replace('-', 'neg')
        dss.append((lyr, '{}_{}_{}'.format(lyr, min_lat_name, max_lat_name), """CENT_LAT > {} AND CENT_LAT <= {}""".format(min_lat, max_lat)))
    
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