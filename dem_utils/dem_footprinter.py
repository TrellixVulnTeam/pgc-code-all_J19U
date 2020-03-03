# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:39:46 2020

@author: disbr007
"""

import argparse
import logging.config
import os
import glob

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import LOGGING_CONFIG
from misc_utils.RasterWrapper import Raster


#### Set up logging
handler_level = 'DEBUG'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)




# cmd = """gdaltindex {} {}""".format(index_name, matches_str)
# run_subprocess(cmd)
 
def raster_footprints(rasters):
    """
    Takes a list of rasters and create a gpd.GeoDataFrame of their footprints and file locations.

    Parameters
    ----------
    rasters : LIST
        List of raster file paths.

    Returns
    -------
    gpd.GeoDataFrame.

    """
    logger.info('Iterating over rasters...')
    df = gpd.GeoDataFrame(columns=['location','geometry'])
    for fname in tqdm(rasters):
        r = Raster(fname)
        bbox = r.raster_bbox()
        df = df.append({'location':fname, 'geometry': bbox}, ignore_index=True)
    
    # Set crs of dataframe to the last raster -- this assumes they are all the same
    df.crs = r.prj.wkt
    
    return df


def main(directory, out_footprint, pattern='\*.tif', dryrun=False):
    # Find files that match the given pattern    
    full_pattern = directory + pattern
    matches = glob.glob(full_pattern)
    logger.info('Matching rasters: {}'.format(len(matches)))
    
    # Create dataframe of footprints
    if not dryrun:
        df = raster_footprints(matches)
    
        logger.info('Writing index to file...')
        df.to_file(out_footprint)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-o', '--out_footprint', 
                        type=os.path.abspath, 
                        required=True,
                        help='Path to create output shapefile.')
    
    parser.add_argument('-i', '--input_directory',
                        type=os.path.abspath,
                        default=os.getcwd(),
                        help='Directory of rasters to parse.')
    
    parser.add_argument('-p', '--pattern',
                        type=str,
                        default='.tif',
                        help="""Pattern rasters must match to include. Must start with "/",
                                I.e. "/*/*dem*.tif""")
    
    parser.add_argument('--dryrun', action='store_true',
                        help='Find matches only.')
    
    args = parser.parse_args()
    
    main(args.input_directory, args.out_footprint, args.pattern, args.dryrun)