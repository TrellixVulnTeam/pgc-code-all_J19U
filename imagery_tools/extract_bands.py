import argparse
import os
from pathlib import Path
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')


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


def extract_bands(img, bands, dst=None, dryrun=False):
    img = Path(img)
    if not dst:
        dst = img.parent / '{}_b{}{}'.format(img.stem, str(bands)[1:-1].replace(', ', ''), img.suffix)

    logger.info('Source image: {}'.format(img))
    logger.info('Destination:  {}'.format(dst))
    logger.info('Bands: {}'.format(str(bands)[1:-1]))

    logger.info('Extracting bands and writing to new file...')
    bands_str = ' '.join(['-b {}'.format(b) for b in bands])
    cmd = 'gdal_translate {} {} {}'.format(bands_str, img, dst)
    logger.debug(cmd)
    if not dryrun:
        run_subprocess(cmd)
    else:
        logger.info('(dryrun) cmd: {}'.format(cmd))

    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input_img', type=os.path.abspath,
                        help='Source multiband image to extract from.')
    parser.add_argument('-o', '--output_img', type=os.path.abspath,
                        help='Path to write image with extracted bands to.')
    parser.add_argument('-b', '--bands', type=int, nargs='*',
                        help='Band numbers in source imagery to extract.'
                             'They will be written to output_img in the '
                             'order supplied here.')
    parser.add_argument('--dryrun', action='store_true')

    args = parser.parse_args()

    extract_bands(args.input_img, args.bands, args.output_img, dryrun=args.dryrun)
