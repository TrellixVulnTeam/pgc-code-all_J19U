import argparse
import logging.config
import os
import subprocess
from subprocess import PIPE, STDOUT

from misc_utils.logging_utils import create_logger

def submit_job(args):

    src = args.src
    dst = args.dst
    of = args.out_format
    dryrun = args.dryrun

    # Build cmd
    qsub_script = '/mnt/pgc/data/scratch/jeff/code/pgc-code-all/imagery_tools/convert_format.sh'
    cmd = 'qsub -v p1="{}",p2="{}",p3={} {}'.format(src,
                                                    dst,
                                                    of,
                                                    qsub_script)

    if dryrun:
        logger.info(cmd)
    else:
        p = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output = p.stdout.read()
        logger.info(output.decode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--src',
                        type=os.path.abspath,
                        help='Image to convert.')
    parser.add_argument('-o', '--dst',
                        type=os.path.abspath,
                        help='Output image.')
    parser.add_argument('-f', '--out_format')
    parser.add_argument('-d', '--dryrun', action='store_true')

    args = parser.parse_args()

    # Set up logger
    handler_level = 'INFO'

    logger = create_logger(__name__, 'sh',
                           handler_level=handler_level)

    submit_job(args)
