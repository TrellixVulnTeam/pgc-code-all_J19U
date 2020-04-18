import os, string, sys, shutil, math, glob, re, argparse, logging
print "Importing arcpy..."
import arcpy
print "Imported arcpy"

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
    dss = [
        (lyr, lyr+"_arctic", """CENT_LAT >= 49"""),
        (lyr, lyr+"_antarctic", """CENT_LAT <= -50"""),
        (lyr, lyr+"_hma", """CENT_LAT >= 25 AND CENT_LAT <= 53 AND CENT_LONG >= 65 AND CENT_LONG <= 110"""),
        (lyr, lyr+"_p1bs", """PROD_CODE = 'P1BS'"""),
        (lyr+"_arctic", lyr+"_arctic_p1bs", """PROD_CODE = 'P1BS'"""),
        (lyr+"_antarctic", lyr+"_antarctic_p1bs", """PROD_CODE = 'P1BS'"""),
        (lyr+"_hma", lyr+"_hma_p1bs", """PROD_CODE = 'P1BS'"""),
    ]

    for ds in dss:
        src, dst, exp = ds
        logger.info("Calculating {}".format(dst))
        arcpy.FeatureClassToFeatureClass_conversion(src,gdb,dst,exp)
        logger.info("Adding index to {}".format(dst))
        arcpy.AddIndex_management(dst,"CATALOG_ID","catid")

    ## Add index to base table
    logger.info("Adding index to {}".format(lyr))
    arcpy.AddIndex_management(lyr,"CATALOG_ID","catid")

if __name__ == '__main__':
    main()