import argparse
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')

# Params
wbt = 'whitebox_tools.exe'
edge_density = 'EdgeDensity'


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


def wbt_edge_density(in_dem, out_path=None, filter_size=11, norm_diff=2, out_dir=None, dryrun=False):
    in_dem = Path(in_dem)
    if not out_path:
        out_path = Path(out_dir) / '{}_ED_f{}nd{}{}'.format(in_dem.stem, filter_size,
                                                            str(norm_diff).replace('.', 'x'),
                                                            in_dem.suffix)

    logger.info('Input DEM: {}'.format(in_dem))
    logger.info('Output:    {}'.format(out_path))
    cmd = '{} -r={} --dem={} --output={} --filter={} --norm_diff={}'.format(wbt, edge_density, in_dem, out_path,
                                                                            filter_size, norm_diff)
    logger.debug('Cmd: {}'.format(cmd))
    
    if not dryrun:
        logger.info('Running WBT EdgeDensity')
        run_subprocess(cmd)
    else:
        logger.info('Dryrun -- command: {}'.format(cmd))
    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Wrapper for Whitebox Tools EdgeDensity:\n'
                                     'https://jblindsay.github.io/wbt_book/available_tools'
                                     '/geomorphometric_analysis.html#edgedensity')

    out_group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('-i', '--dem', type=os.path.abspath,
                        help='Path to DEM to compute curvature on.')
    out_group.add_argument('-o', '--output', type=os.path.abspath,
                           help='Path to write curvature to.')
    out_group.add_argument('-od', '--out_directory', type=os.path.abspath,
                           help='Directory to write output to with standardized name.')
    parser.add_argument('-f', '--filter', type=int,
                        help='Size of filter kernel.')
    parser.add_argument('-nd', '--norm_diff', type=float,
                        help='Maximum difference in normal vectors, in degrees.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without performing.')

    args = parser.parse_args()

    wbt_edge_density(in_dem=args.dem, out_path=args.output,
                     filter_size=args.filter, norm_diff=args.norm_diff,
                     out_dir=args.out_directory, dryrun=args.dryrun)
