# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:41:22 2020

@author: disbr007
"""

import argparse
import datetime
import logging.config
import math
import os
import subprocess
from subprocess import PIPE

# from osgeo import gdal

from misc_utils.logging_utils import LOGGING_CONFIG, create_logger


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


def otb_texture_haralick(img,
                         channel=1,
                         texture='simple',
                         img_min=0, img_max=255,
                         xrad=2, yrad=2,
                         xoff=1, yoff=1,
                         nbin=8,
                         out_image=None):
    """
    Wrapper for OTB Haralick texture features. Computes Haralick, advanced 
    and higher order texture features on every pixel in the selected channel
    of the input image. The output image is multi band with a feature per band.

    Parameters
    ----------
    img : os.path.abspath
        input image to compute features on.
    channel : int, optional
        channel index in image input to be processed. The default is 1.
    texture : str, optional
        One of [simple|higher|advanced]. The default is 'simple'.
    img_min : float, optional
        input image minimum. The default is 0.
    img_max : float, optional
        input image maximum. The default is 255.
    xrad : int, optional
        the X radius of the processing neighborhood. The default is 2.
    yrad : int, optional
        the Y radius of the processing neighborhood. The default is 2.
    xoff : int, optional
        the deltaX offset for the co-occur computation. The default is 1.
    yoff : int, optional
        the deltaY offset for the co-occur computation. The default is 1.
    nbin : int, optional
        the number of bin per axis for histogram generation. The default is 8.
    out_image : os.path.abspath, optional
        path to write compute texture image to. The default is None.

    Returns
    -------
    None.

    """
    # Build the command
    cmd = """otbcli_HaralickTextureExtraction
             -in {}
             -channel {}
             -texture {}
             -parameters.min {}
             -parameters.max {}
             -parameters.xrad {}
             -parameters.yrad {}
             -parameters.xoff {}
             -parameters.yoff {}
             -parameters.nbbin {}
             -out {}""".format(img,
                               channel, texture,
                               img_min, img_max,
                               xrad, yrad,
                               xoff, yoff,
                               nbin,
                               out_image)
    
    # Remove whitespace, newlines
    cmd = cmd.replace('\n', '')
    cmd = ' '.join(cmd.split())
    logger.info(cmd)
    
    # Run command
    logger.debug(cmd)
    # If run too quickly, check OTB env is active
    run_time_start = datetime.datetime.now()
    run_subprocess(cmd)
    run_time_finish = datetime.datetime.now()
    run_time = run_time_finish - run_time_start
    too_fast = datetime.timedelta(seconds=10)
    if run_time < too_fast:
        logger.warning("""Execution completed quickly, likely due to an error. Did you activate
                          OTB env first?
                          "C:\OSGeo4W64\OTB-6.6.1-Win64\OTB-6.6.1-Win64\otbenv.bat" or
                          module load otb/6.6.1
                          """)
    logger.info('HaralickTextureExtraction finished. Runtime: {}'.format(str(run_time)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_image',
                        type=os.path.abspath,
                        help='Image to compute features on.')
    parser.add_argument('-o', '--out_image',
                        type=os.path.abspath,
                        default=None,
                        help="""Path to write texture image to. Alternatively
                                just supply -od and the name will be created 
                                in that directory in a standardized manner:
                                [input filename]c[channe]t[texture]imin[]imax[]xr[]yr[]xo[]yo[]nb[].tif""")
    parser.add_argument('-od', '--out_dir',
                        type=os.path.abspath,
                        help="""Alternatively to specifying out_vector path, specify
                                just the output directory and the name will be
                                created in a standardized fashion following:
                                [input filename]c[channe]t[texture]imin[]imax[]xr[]yr[]xo[]yo[]nb[].tif""")
    parser.add_argument('-c', '--channel',
                        default=1,
                        type=int,
                        help='Channel in input to compute texture on.')
    parser.add_argument('-t', '--texture',
                        # nargs='+',
                        choices=['simple', 'advanced', 'higher'],
                        help="""Texture set selection, may choose more than one. If multiple,
                                output is multiband image, one band per selection.""")
    parser.add_argument('-imn', '--image_min',
                        type=float,
                        help='Minimum value in the input image.')
    parser.add_argument('-imx', '--image_max',
                        type=float,
                        help='Maximum value in the input image.')
    parser.add_argument('-xr', '--xradius',
                        default=2,
                        type=int,
                        help='the X radius of the processing neighborhood.')
    parser.add_argument('-yr', '--yradius',
                        default=2,
                        type=int,
                        help='the Y radius of the processing neighborhood.')
    parser.add_argument('-xo', '--x_offset',
                        default=1,
                        type=int,
                        help='the deltaX offset for the co-occur computation')
    parser.add_argument('-yo', '--y_offset',
                        default=1,
                        type=int,
                        help='the deltaY offset for the co-occur computation')
    parser.add_argument('-nb', '--num_bins',
                        default=8,
                        type=int,
                        help='the number of bin per axis for histogram generation. The default is 8.')
    parser.add_argument('-l', '--log_file',
                        type=os.path.abspath,
                        default='otb_lsms_log.txt',
                        help='Path to write log file to.')
    parser.add_argument('-ld', '--log_dir',
                        type=os.path.abspath,
                        help="""Directory to write log to, with standardized name following
                                out vector naming convention.""")

    
    args = parser.parse_args()
    
    img = args.input_image
    out_image = args.out_image
    out_dir = args.out_dir
    channel = args.channel
    texture = args.texture
    img_min = args.image_min
    img_max = args.image_max
    xrad = args.xradius
    yrad = args.yradius
    xoff = args.x_offset
    yoff = args.y_offset
    nbin = args.num_bins
    
    #### Set up logger
    handler_level = 'INFO'
    log_file = args.log_file
    log_dir = args.log_dir
    if not log_file:
        if not log_dir:
            log_dir = os.path.dirname(out_image)
        log_name = os.path.basename(out_image).replace('.tif', '_log.txt')
        log_file = os.path.join(log_dir, log_name)

    logger = create_logger(__name__, 'fh',
                           handler_level='DEBUG',
                           filename=args.log_file)
    logger = create_logger(__name__, 'sh',
                           handler_level=handler_level)
    
    #### Argument verification
    # if not img_min and not img_max:
    #     ds = gdal.Open(img)
    #     band = ds.GetRasterBand(channel)
        
    #     stats = band.GetStatistics(True, True)
        
    #     img_min = math.floor(stats[0])
    #     img_max = math.ceil(stats[1])
    
    if out_image is None:
        if out_dir is None:
            out_dir = os.path.dirname(img)
        out_name = os.path.basename(img).split('.')[0]
        out_name = '{}_c{}t{}_imin{}imax{}xr{}yr{}xo{}yo{}nb{}.tif'.format(out_name,
                                                                         channel,
                                                                         texture[:3],
                                                                         str(img_min).replace('.', 'x'),
                                                                         str(img_max).replace('.', 'x'),
                                                                         xrad, yrad,
                                                                         xoff, yoff,
                                                                         nbin,
                                                                         )
        out_image = os.path.join(out_dir, out_name)

        
    # Run command    
    otb_texture_haralick(img=img,
                         out_image=out_image,
                         channel=channel,
                         texture=texture,
                         img_min=img_min,
                         img_max=img_max,
                         xrad=xrad,
                         yrad=yrad,
                         xoff=xoff,
                         yoff=yoff,
                         nbin=8,
                         )
    
    
