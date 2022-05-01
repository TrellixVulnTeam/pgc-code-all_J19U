import argparse
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')

# Params
wbt = 'whitebox_tools'
sar = 'SurfaceAreaRatio'


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):
        logger.info('(subprocess) {}'.format(line.decode()))
    proc_err = ""
    for line in iter(proc.stderr.readline, b''):
        proc_err += line.decode()
    if proc_err:
        logger.info('(subprocess) {}'.format(proc_err))
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


def wbt_sar(in_dem, out_sar=None, out_dir=None, dryrun=False):
    in_dem = Path(in_dem)
    if not out_sar:
        if not out_dir:
            out_dir = in_dem.parent
        else:
            out_dir = Path(out_dir)
        out_sar = out_dir / '{}_sar{}'.format(in_dem.stem, in_dem.suffix)

    logger.info('Input DEM: {}'.format(in_dem))
    logger.info('Output:    {}'.format(out_sar))
    cmd = '{} -r={} --dem={} --output={}'.format(wbt, sar, in_dem, out_sar)
    logger.debug('Cmd: {}'.format(cmd))
    
    if not dryrun:
        logger.info('Running WBT SurfaceAreaRatio...')
        run_subprocess(cmd)
    else:
        logger.info(cmd)

    logger.info('Done.')

    return out_sar


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--dem', type=os.path.abspath,
                        help='Path to DEM to compute SurfaceAreaRatio on.')
    parser.add_argument('-o', '--output', type=os.path.abspath,
                        help='Path to write SurfaceAreaRatio to.')
    parser.add_argument('-od', '--out_directory', type=os.path.abspath,
                        help='Directory to write curvature to with standardized name.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')

    args = parser.parse_args()

    wbt_sar(in_dem=args.dem, out_sar=args.output,
                  out_dir=args.out_directory,
                  dryrun=args.dryrun)