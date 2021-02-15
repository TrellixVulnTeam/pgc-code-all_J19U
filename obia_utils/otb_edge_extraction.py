# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 14:22:54 2020

@author: disbr007
"""
import argparse
import datetime
import os
from pathlib import Path
import platform
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger, create_logfile_path
from misc_utils.gdal_tools import gdal_polygonize


logger = create_logger(__name__, 'sh', 'DEBUG')

# Constants
# Init OTB env
if platform.system() == 'Windows':
    otb_init = r"C:\OTB-7.1.0-Win64\OTB-7.1.0-Win64\otbenv.bat"
elif platform.system() == 'Linux':
    otb_init = r"module load OTB"

GRADIENT = 'gradient'
SOBEL = 'sobel'
TOUZI = 'touzi'

# Function definition
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        logger.info(line.decode())
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


def create_outname(img=None, out_edge=None, out_dir=None, out_fmt=None,
                   edge_filter=GRADIENT, channel=1,
                   touzi_xradius=1,
                   touzi_yradius=1):
    # Create output names as needed
    img_p = Path(img)
    if out_fmt is None:
        out_fmt = img_p.suffix
    if out_edge is None:
        if out_dir is None:
            out_dir = img_p.parent
        else:
            out_dir = Path(out_dir)
        out_name = '{}_c{}{}'.format(img_p.stem, channel, edge_filter)
        if edge_filter == TOUZI:
            out_name = '{}_x{}y{}'.format(out_name, touzi_xradius, touzi_yradius)

        out_name = '{}{}'.format(out_name, out_fmt)

        out_edge = out_dir / out_name

    return out_edge


def otb_edge_extraction(img: str, out_edge: str = None, out_dir: str = None,
                        out_fmt: str = None,
                        edge_filter: str = GRADIENT,
                        channel: int = 1,
                        touzi_xradius: int = 1,
                        touzi_yradius: int = 1,
                        init_otb_env: bool = True):
    """
    Run the Orfeo Toolbox GenericRegionMerging command via the command line.
    Requires that OTB environment is activated

    Parameters
    ----------
    img : os.path.abspath
        Path to source to be segmented.
    threshold : float,
        Threshold within which to merge. The default is 0.
    out_edge: os.path.abspath, optional
        Path to write segmentation image to. The default is None.
    edge_filter: str
        Filter to use, one of: gradient, sobel, touzi
    touzi_xradius: str
        X radius of filter if touzi
    touzi_yradius: str
        Y radius of filter if touzi
    out_fmt : str
        Format to write segmentation out as {raster, vector}

    Returns
    -------
    None.

    """
    # Create ouput name based on input parameters
    if out_edge is None:
        out_edge = create_outname(img=img,
                                  out_edge=out_edge,
                                  out_dir=out_dir,
                                  out_fmt=out_fmt,
                                  edge_filter=edge_filter,
                                  channel=channel,
                                  touzi_xradius=touzi_xradius,
                                  touzi_yradius=touzi_yradius)

    out_edge_parent = Path(out_edge).parent
    if not out_edge_parent.exists():
        logger.info('Creating directory for output:\n '
                    '{}'.format(out_edge_parent))
        os.makedirs(out_edge_parent)

    # Log input image information
    logger.info("""Running OTB Edge Extraction...
                    Input image: {}
                    Out image:   {}
                    Out format:  {}
                    Edge filter: {}""".format(Path(img).name, Path(out_edge).name, out_fmt, edge_filter))
    if edge_filter == TOUZI:
        logger.info('Touzi x-radius: {}'.format(touzi_xradius))
        logger.info('Touzi y-radius: {}'.format(touzi_yradius))

    # Build the command
    cmd = """otbcli_EdgeExtraction
             -in {}
             -out {}
             -filter {}
             -channel {}""".format(img, out_edge, edge_filter, channel)
    if edge_filter == TOUZI:
        cmd += " -filter.touzi.xradius {} -filter.touzi.yradius {}".format(touzi_xradius, touzi_yradius)

    # Remove whitespace, newlines
    cmd = cmd.replace('\n', '')
    cmd = ' '.join(cmd.split())

    # Environment init before calling command
    if init_otb_env:
        cmd = '{} && {}'.format(otb_init, cmd)

    # Run command
    logger.debug(cmd)

    # If run too quickly, check OTB env is active
    run_time_start = datetime.datetime.now()
    run_subprocess(cmd)
    run_time_finish = datetime.datetime.now()
    run_time = run_time_finish - run_time_start
    too_fast = datetime.timedelta(seconds=1)
    if run_time < too_fast:
        logger.warning("Execution completed quickly, likely due to an error. "
                       "Did you activate OTB env first?\n"
                       "'C:\OTB-7.1.0-Win64\OTB-7.1.0-Win64\otbenv.bat'\nor\n"
                       "module load otb/6.6.1")
    logger.info('EdgeExtraction finished. Runtime: {}'.format(str(run_time)))
    
    return out_edge


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-i', '--image_source',
                        type=os.path.abspath,
                        help='Path to image to be segmented')
    parser.add_argument('-o', '--out_edge',
                        type=os.path.abspath,
                        help='Path to write segmentation image to')
    parser.add_argument('-od', '--out_dir',
                        type=os.path.abspath,
                        help="""Alternatively to specifying out_vector path, specify
                                just the output directory and the name will be
                                created in a standardized fashion following:
                                [input_filename]_c[criterion]t[threshold]ni[num_iterations]s[speed]spec[spectral]spat[spatial].tif""")
    parser.add_argument('-of', '--out_fmt',
                        help='Format of output image. Defaults to format of input. '
                             'E.g. ".tif"')
    parser.add_argument('-e', '--edge_filter', choices=[GRADIENT, SOBEL, TOUZI],
                        help='Filter to use.')
    parser.add_argument('-c', '--channel', type=int, default=1,
                        help='The band in the input image to compute on. 1 indexed')
    parser.add_argument('-tx', '--touzi_xradius', type=int, default=1,
                        help='The X radius of the filter if using touzi.')
    parser.add_argument('-ty', '--touzi_yradius', type=int, default=1,
                        help='The Y radius of the filter if using touzi.')
    parser.add_argument('-l', '--log_file',
                        type=os.path.abspath,
                        default='otb_edge_extraction.log',
                        help='Path to write log file to.')
    parser.add_argument('-ld', '--log_dir',
                        type=os.path.abspath,
                        help="""Directory to write log to, with standardized name following
                                out tif naming convention.""")

    args = parser.parse_args()

    image_source = args.image_source
    out_edge = args.out_edge
    out_dir = args.out_dir
    out_fmt = args.out_fmt
    edge_filter = args.edge_filter
    channel = args.channel
    touzi_xradius = args.touzi_xradius
    touzi_yradius = args.touzi_yradius

    # Set up logger
    handler_level = 'INFO'
    log_file = args.log_file
    log_dir = args.log_dir
    if not log_file:
        if not log_dir:
            log_dir = os.path.dirname(out_edge)
        log_file = create_logfile_path(Path(__file__).stem, logdir=log_dir)

    logger = create_logger(__name__, 'fh',
                           handler_level='DEBUG',
                           filename=args.log_file)

    # Run EdgeExtraction
    otb_edge_extraction(img=image_source,
                        out_edge=out_edge,
                        out_dir=out_dir,
                        out_fmt=out_fmt,
                        edge_filter=edge_filter,
                        channel=channel,
                        touzi_xradius=touzi_xradius,
                        touzi_yradius=touzi_yradius)
