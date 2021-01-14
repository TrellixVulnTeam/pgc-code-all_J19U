import argparse
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')

# Params
wbt = 'whitebox_tools.exe'
curv_prof = 'ProfileCurvature'
curv_plan = 'PlanCurvature'
curv_tang = 'TangentialCurvature'
curv_tot = 'TotalCurvature'


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


def wbt_curvature(in_dem, out_curv=None, out_dir=None, curv_type=curv_prof, dryrun=False):
    in_dem = Path(in_dem)
    if not out_curv:
        if not out_dir:
            out_dir = in_dem.parent
        else:
            out_dir = Path(out_dir)
        out_curv = out_dir / '{}_{}{}'.format(in_dem.stem, curv_type, in_dem.suffix)

    logger.info('Input DEM: {}'.format(in_dem))
    logger.info('Output:    {}'.format(out_curv))
    logger.info('Type:      {}'.format(curv_type))
    cmd = '{} -r={} --dem={} --output={}'.format(wbt, curv_type, in_dem, out_curv)
    logger.debug('Cmd: {}'.format(cmd))
    
    if not dryrun:
        logger.info('Running WBT Curvature - {}...'.format(curv_type))
        run_subprocess(cmd)
    else:
        logger.info(cmd)

    logger.info('Done.')

    return out_curv


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--dem', type=os.path.abspath,
                        help='Path to DEM to compute curvature on.')
    parser.add_argument('-o', '--output', type=os.path.abspath,
                        help='Path to write curvature to.')
    parser.add_argument('-od', '--out_directory', type=os.path.abspath,
                        help='Directory to write curvature to with standardized name.')
    parser.add_argument('-t', '--curv_type', choices=[curv_prof, curv_plan, curv_tang, curv_tot],
                        default=curv_prof,
                        help='Type of curvature to compute.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')

    args = parser.parse_args()

    wbt_curvature(in_dem=args.dem, out_curv=args.output, out_dir=args.out_directory,
                  curv_type=args.curv_type, dryrun=args.dryrun)