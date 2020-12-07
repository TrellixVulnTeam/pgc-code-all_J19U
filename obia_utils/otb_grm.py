# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:22:54 2020

@author: disbr007
"""
import argparse
import datetime
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from osgeo import gdal

from misc_utils.logging_utils import create_logger, create_logfile_path
from misc_utils.gdal_tools import gdal_polygonize
# from cleanup_objects import mask_objs
# from misc_utils.RasterWrapper import Raster


# Function definition
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        logger.info(line.decode())
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


def otb_grm(img,
            threshold,
            out_seg=None,
            out_format='raster',
            criterion='bs',
            niter=0,
            speed=0,
            cw=0.5,
            sw=0.5,):
    """
    Run the Orfeo Toolbox GenericRegionMerging command via the command line.
    Requires that OTB environment is activated

    Parameters
    ----------
    img : os.path.abspath
        Path to source to be segmented.
    threshold : float,
        Threshold within which to merge. The default is 0.
    out_seg: os.path.abspath, optional
        Path to write segmentation image to. The default is None.
    criterion : str, optional
        Homogeneity criterion to use. The default is 'bs'. One of: [bs, ed, fls]
    niter : int
        Merging iterations, 0 = no additional merging
    speed : int, optional
        Boost segmentation speed. The default is 0.
    cw : float, optional
        How much to consider spectral similarity. The default is 0.5.
    sw : float, optional
        How much to consider spatial similarity, i.e. shape. The default is 0.5.

    Returns
    -------
    None.

    """
    # # Log input image information
    # TODO: This is not working due to OTB using it's own GDAL.
    # src = Raster(img)
    # x_sz = src.x_sz
    # y_sz = src.y_sz
    # depth = src.depth
    # src = None

    # logger.info("""Running OTB Generic Region Merging...
    #                Input image: {}
    #                Image X Size: {}
    #                Image Y Size: {}
    #                Image # Bands: {}
    #                Out image:   {}
    #                Criterion:   {}
    #                Threshold:   {}
    #                # Iterate:   {}
    #                Spectral:    {}
    #                Spatial:     {}""".format(img, x_sz, y_sz, depth,
    #                                          out_seg, criterion, threshold,
    #                                          niter, cw, sw))


    logger.info("""Running OTB Generic Region Merging...
                    Input image: {}
                    Out image:   {}
                    Out format:  {}
                    Criterion:   {}
                    Threshold:   {}
                    # Iterate:   {}
                    Spectral:    {}
                    Spatial:     {}""".format(img, out_seg, out_format,
                                              criterion, threshold,
                                              niter, cw, sw))
    # Build the command
    cmd = """otbcli_GenericRegionMerging
             -in {}
             -out {}
             -criterion {}
             -threshold {}
             -niter {}
             -cw {}
             -sw {}""".format(img, out_seg,
                              criterion,
                              threshold,
                              niter,
                              cw,
                              sw)

    # Remove whitespace, newlines
    cmd = cmd.replace('\n', '')
    cmd = ' '.join(cmd.split())

    # Run command
    logger.debug(cmd)
    # If run too quickly, check OTB env is active
    run_time_start = datetime.datetime.now()
    run_subprocess(cmd)
    run_time_finish = datetime.datetime.now()
    run_time = run_time_finish - run_time_start
    too_fast = datetime.timedelta(seconds=10)
    if run_time < too_fast:
        logger.warning("Execution completed quickly, likely due to an error. "
                       "Did you activate OTB env first?\n"
                       "'C:\OTB-7.1.0-Win64\OTB-7.1.0-Win64\otbenv.bat'\nor\n"
                       "module load otb/6.6.1")
    logger.info('GenericRegionMerging finished. Runtime: {}'.format(str(run_time)))
    
    if out_format == 'vector':
        logger.info('Vectorizing...')
        vec_seg = out_seg.replace('tif', 'shp')
        gdal_polygonize(img=out_seg, out_vec=vec_seg, fieldname='label')
        logger.info('Segmentation created at: {}'.format(vec_seg))
        logger.debug('Removing raster segmentation...')
        os.remove(out_seg)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-i', '--image_source',
                        type=os.path.abspath,
                        help='Path to image to be segmented')
    parser.add_argument('-o', '--out_seg',
                        type=os.path.abspath,
                        help='Path to write segmentation image to')
    parser.add_argument('-od', '--out_dir',
                        type=os.path.abspath,
                        help="""Alternatively to specifying out_vector path, specify
                                just the output directory and the name will be
                                created in a standardized fashion following:
                                [input_filename]_c[criterion]t[threshold]ni[num_iterations]s[speed]spec[spectral]spat[spatial].tif""")
    parser.add_argument('-of', '--out_format', choices=['raster', 'vector'],
                        help='Format of output segmentation.')
    parser.add_argument('-t', '--threshold',
                        type=float,
                        default=100,
                        help='Threshold within which to merge.')
    parser.add_argument('-c', '--criterion',
                        type=str,
                        default='bs',
                        choices=['bs', 'ed', 'fls'],
                        help="""Homogeneity criterion to use, one of:
                                [bs, ed, fls]
                                Baatz and Schape
                                Euclidian Distance
                                Full Lambda Schedule""")
    parser.add_argument('-ni', '--num_iterations',
                        type=int,
                        default=0,
                        help='Merging iterations, 0 = no additional merging.')
    parser.add_argument('-s', '--speed',
                        type=int,
                        default=0,
                        help='')
    parser.add_argument('-cw', '--spectral',
                        type=float,
                        default=0.5,
                        help='How much to consider spectral similarity')
    parser.add_argument('-sw', '--spatial',
                        type=float,
                        default=0.5,
                        help='How much to consider spatial similarity, i.e. '
                             'shape')
    parser.add_argument('-l', '--log_file',
                        type=os.path.abspath,
                        default='otb_lsms_log.txt',
                        help='Path to write log file to.')
    parser.add_argument('-ld', '--log_dir',
                        type=os.path.abspath,
                        help="""Directory to write log to, with standardized name following
                                out tif naming convention.""")

    args = parser.parse_args()

    image_source = args.image_source
    out_seg = args.out_seg
    out_dir = args.out_dir
    out_format = args.out_format
    threshold = args.threshold
    criterion = args.criterion
    num_iterations = args.num_iterations
    speed = args.speed
    spectral = args.spectral
    spatial = args.spatial

    # Create output names as needed
    if out_seg is None:
        if out_dir is None:
            out_dir = os.path.dirname(image_source)
        out_name = os.path.basename(image_source).split('.')[0]
        out_name = '{}_{}t{}ni{}s{}spec{}spat{}.tif'.format(out_name, criterion,
                                                            str(threshold).replace('.', 'x'),
                                                            num_iterations, speed,
                                                            str(spectral).replace('.', 'x'),
                                                            str(spatial).replace('.', 'x'))
        out_seg = os.path.join(out_dir, out_name)

    # Set up logger
    handler_level = 'INFO'
    log_file = args.log_file
    log_dir = args.log_dir
    if not log_file:
        if not log_dir:
            log_dir = os.path.dirname(out_seg)
        log_file = create_logfile_path(Path(__file__).stem, logdir=log_dir)

    logger = create_logger(__name__, 'fh',
                           handler_level='DEBUG',
                           filename=args.log_file)
    logger = create_logger(__name__, 'sh',
                           handler_level=handler_level)

    # Run segmentation
    otb_grm(img=image_source,
            threshold=threshold,
            out_seg=out_seg,
            out_format=out_format,
            criterion=criterion,
            niter=num_iterations,
            speed=speed,
            cw=spectral,
            sw=spatial)
