
import argparse
import logging.config
import os
import subprocess
from subprocess import PIPE, STDOUT

from misc_utils.logging_utils import LOGGING_CONFIG


#### Set up logger
handler_level = 'INFO'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def submit_job(args):
    """
    Submits otb_lsms.py to scheduler.
    """
    image_source = args.image_source
    out_vector = args.out_vector
    spatialr = args.spatial_radius
    ranger = args.range_radius
    minsize = args.minsize
    tilesize_x = args.tilesize_x
    tilesize_y = args.tilesize_y
    dryrun = args.dryrun

    # Build cmd
    otb_lsms_script = '/mnt/pgc/data/scratch/jeff/code/pgc-code-all/obia_utils/qsub_otb_lsms.sh'
    cmd = 'qsub -v p1="{}",p2="{}",p3={},p4={},p6={},p7={},p8={} {}'.format(image_source,
                                                                            out_vector,
                                                                            spatialr,
                                                                            ranger,
                                                                            minsize,
                                                                            tilesize_x,
                                                                            tilesize_y,
                                                                            otb_lsms_script)

    if dryrun:
        logger.info(cmd)
    else:
        p = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output = p.stdout.read()
        logger.info(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--image_source',
                        type=os.path.abspath,
                        help='Image to segment.')
    parser.add_argument('-o', '--out_vector',
                        type=os.path.abspath,
                        help='Output vector.')
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
    parser.add_argument('-d', '--dryrun', action='store_true')

    args = parser.parse_args()

    submit_job(args)
