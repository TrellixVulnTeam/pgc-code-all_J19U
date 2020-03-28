# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:22:54 2020

@author: disbr007
"""
import argparse
import datetime
import logging.config
import os
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import LOGGING_CONFIG, create_logger


#### Set up logger
# handler_level = 'INFO'
# logging.config.dictConfig(LOGGING_CONFIG(handler_level))
# logger = logging.getLogger(__name__)


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
             out_vector=None,
             ram=256):
    """
    Run the Orfeo Toolbox LargeScaleMeanShift command via the command
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
             -mode.vector.out {}""".format(img, spatialr, ranger, minsize,
                                           tilesize_x, tilesize_y, out_vector)
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
                Output vector: {}""".format(img, spatialr, ranger, minsize,
                                            tilesize_x, tilesize_y, out_vector))

    logger.info(cmd)
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
    logger.info('Large-Scale-Mean-Shift finished. Runtime: {}'.format(str(run_time)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--image_source',
                        type=os.path.abspath,
                        help='Image to segment.')
    parser.add_argument('-o', '--out_vector',
                        type=os.path.abspath,
                        help='Output vector.')
    parser.add_argument('-od', '--out_dir',
                        type=os.path.abspath,
                        help="""Alternatively to specifying out_vector path, specify
                                just the output directory and the name will be
                                created in a standardized fashion following:
                                [input_filename]_sr[sr]rr[rr]ms[ms]tx[tx]ty[ty].shp""")
    parser.add_argument('-sr', '--spatial_radius',
                        type=int,
                        default=5,
                        help="""Spatial radius -- Default value: 5
                                Radius of the spatial neighborhood for averaging.
                                Higher values will result in more smoothing and
                                higher processing time.""")
    parser.add_argument('-rr', '--range_radius',
                        type=float,
                        default=15,
                        help="""Range radius -- Default value: 15
                                Threshold on spectral signature euclidean distance
                                (expressed in radiometry unit) to consider neighborhood
                                pixel for averaging. Higher values will be less
                                edge-preserving (more similar to simple average in neighborhood),
                                whereas lower values will result in less noise smoothing.
                                Note that this parameter has no effect on processing time.""")
    parser.add_argument('-ms', '--minsize',
                        type=int,
                        default=50,
                        help="""Minimum Segment Size -- Default value: 50
                                Minimum Segment Size. If, after the segmentation, a segment is of
                                size strictly lower than this criterion, the segment is merged with
                                the segment that has the closest sepctral signature.""")
    parser.add_argument('-tx', '--tilesize_x',
                        type=int,
                        default=500,
                        help="""Size of tiles in pixel (X-axis) -- Default value: 500
                                Size of tiles along the X-axis for tile-wise processing.""")
    parser.add_argument('-ty', '--tilesize_y',
                        type=int,
                        default=500,
                        help="""Size of tiles in pixel (Y-axis) -- Default value: 500
                                Size of tiles along the Y-axis for tile-wise processing.""")
    parser.add_argument('-l', '--log_file',
                        type=os.path.abspath,
                        help='Path to write log file to.')
    parser.add_argument('-ld', '--log_dir',
                        type=os.path.abspath,
                        help="""Directory to write log to, with standardized name following
                                out vector naming convention.""")

    args = parser.parse_args()

    image_source = args.image_source
    out_vector = args.out_vector
    out_dir = args.out_dir
    spatialr = args.spatial_radius
    ranger = args.range_radius
    minsize = args.minsize
    tilesize_x = args.tilesize_x
    tilesize_y = args.tilesize_y

    # Build out vector path if not provided
    if out_vector is None:
        if out_dir is None:
            out_dir = os.path.dirname(image_source)
        out_name = os.path.basename(image_source).split('.')[0]
        out_name = '{}_sr{}_rr{}_ms{}_tx{}_ty{}.shp'.format(out_name, spatialr, str(ranger).replace('.', '_'),
                                                            minsize, tilesize_x, tilesize_y)
        out_vector = os.path.join(out_dir, out_name)

    #### Set up logger
    handler_level = 'INFO'
    log_file = args.log_file
    log_dir = args.log_dir
    if not log_file:
        if not log_dir:
            log_dir = os.path.dirname(out_vector)
        log_name = os.path.basename(out_vector).replace('.shp', '_log.txt')
        log_file = os.path.join(log_dir, log_name)

    logger = create_logger(__name__, 'fh',
                           handler_level='DEBUG',
                           filename=args.log_file)
    logger = create_logger(__name__, 'sh',
                           handler_level=handler_level)

    otb_lsms(img=image_source,
             out_vector=out_vector,
             spatialr=spatialr,
             ranger=ranger,
             minsize=minsize,
             tilesize_x=tilesize_x,
             tilesize_y=tilesize_y)
