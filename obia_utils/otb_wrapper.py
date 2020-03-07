# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:22:54 2020

@author: disbr007
"""

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
    

#### Inputs
img = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\imagery\WV02_20150906_clip.tif'

# LSMS parameters
spatialr = 6
ranger = 200
segsize = 400
out_shp = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_sr{}rr{}ss{}.shp'.format(spatialr,
                                                                                                     ranger,
                                                                                                     segsize)

#### Parameters


# Test LSMS
cmd = """otbcli_LargeScaleMeanShift -in {} -spatialr {} -ranger {} -minsize {} -mode.vector.out {}""".format(img,
                                                                                                             spatialr,
                                                                                                             out_shp)

logger.info("""Running OTB Large-Scale-Mean-Shift...
            Input image: {}
            Spatial radius: {}
            Range radius: {}
            Min. segment size: {}
            Output vector: {}""".format(img, spatialr, ranger, segsize, out_shp))
logger.info(cmd)
run_subprocess(cmd)




