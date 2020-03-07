# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:22:54 2020

@author: disbr007
"""
import argparse
import logging.config
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import LOGGING_CONFIG


#### Set up logger
handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


#### Function definition
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        logger.info(line.decode())
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))
    

def otb_lsms(img, 
             spatialr=5, ranger=15, minsize=50, 
             tilesize_x=500, tilesize_y=500,
             out_vector=None):
    """
    Runs the Orfeo Toolbox LargeScaleMeanShift command via the command
    line. Requires that OTB environment is activated.

    Parameters
    ----------
    img : os.path.abspath
        Path to raster to be segmented.
    spatialr : INT
        Spatial radius -- Default value: 5
        Radius of the spatial neighborhood for averaging. 
        Higher values will result in more smoothing and higher processing time.
    ranger : FLOAT
        Range radius -- Default value: 15
        Threshold on spectral signature euclidean distance (expressed in radiometry unit) 
        to consider neighborhood pixel for averaging. 
        Higher values will be less edge-preserving (more similar to simple average in neighborhood), 
        whereas lower values will result in less noise smoothing. 
        Note that this parameter has no effect on processing time..
    minsize : INT
        Minimum Segment Size -- Default value: 50
        Minimum Segment Size. If, after the segmentation, a segment is of size strictly 
        lower than this criterion, the segment is merged with the segment that has the 
        closest sepctral signature.
    tilesize_x : INT
        Size of tiles in pixel (X-axis) -- Default value: 500
        Size of tiles along the X-axis for tile-wise processing.
    tilesize_y : INT
        Size of tiles in pixel (Y-axis) -- Default value: 500
        Size of tiles along the Y-axis for tile-wise processing.
    out_vector : os.path.abspath
        Path to write vectorized segments to.

    Returns
    -------
    Path to out_vector.

    """
    # Build command
    cmd = """otbcli_LargeScaleMeanShift 
             -in {} 
             -spatialr {} 
             -ranger {} 
             -minsize {} 
             -tilesizex {} 
             -tilesizey {} 
             -mode.vector.out {}""".format(img, spatialr,ranger, minsize,
                                           tilesize_x, tilesize_y, out_shp)
    # Remove whitespace, newlines
    cmd = cmd.replace('\n', '')
    cmd = ' '.join(cmd.split())
    
    logger.info("""Running OTB Large-Scale-Mean-Shift...
                Input image: {}
                Spatial radius: {}
                Range radius: {}
                Min. segment size: {}
                Tilesizex: {}
                Tilesizey: {}
                Output vector: {}""".format(img, spatialr, ranger, segsize, 
                                            tilesize_x, tilesize_y, out_shp))
    
    logger.debug(cmd)
    run_subprocess(cmd)


#### Inputs
img = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\imagery\WV02_20150906_clip.tif'

# LSMS parameters
spatialr = 5
ranger = 200
segsize = 400
tilesize = 300
out_shp = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_sr{}rr{}ss{}ts{}.shp'.format(spatialr,
                                                                                                        ranger,
                                                                                                        segsize,
                                                                                                        tilesize)

otb_lsms(img=img, spatialr=spatialr, ranger=ranger, minsize=segsize, tilesize_x=tilesize, tilesize_y=tilesize)
# if __name__ == '__main__':
    