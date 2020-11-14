#tif2jp2_genqsub.py
import argparse
import os
from pathlib import Path
import subprocess

from tqdm import tqdm

from misc_utils.logging_utils import create_logger

qsubscript = Path(__file__).parent / 'tif2jp2_qsub.sh'


def submit_jobs(args):
    logger.info(qsubscript)
    srcdir = args.src
    dstdir = args.dst
    out_format = args.out_format
    out_suffix = args.out_suffix
    dryrun = args.dryrun

    logger.info('Srcdir: {}'.format(srcdir))
    logger.info('Dstdir: {}'.format(dstdir))
    logger.info('Out format: {}'.format(out_format))
    logger.info('Out suffix: {}'.format(out_suffix))
    logger.info('Dryrun: {}'.format(dryrun))

    logger.info('Locating tifs...')
    tifs = [f for f in Path(srcdir).rglob('*.tif')]
    logger.info('Tifs found: {}'.format(len(tifs)))
    for t in tqdm(tifs):
        dst = Path(dstdir) / '{}.{}'.format(t.stem, out_suffix)
        if not dst.exists():
            cmd = 'qsub -l walltime=4:00:00 -l nodes=1:ppn=4 ' \
                  '-v p1="{}",p2="{}",p3="{}" {}'.format(t, dst, out_format,
                                                         qsubscript)
            logger.debug(cmd)
            if not dryrun:
                if not dst.parent.exists():
                    logger.info('Creating subdirectories up to: '
                                '{}'.format(t.parent))
                    os.makedirs(dst.parent)
                subprocess.call(cmd, shell=True)
        else:
            logger.info('File exists, skipping: {}'.format(t.parent / t.name))


if __name__ == '__main__':
    if __name__ == '__main__':
        parser = argparse.ArgumentParser()

        parser.add_argument('-i', '--src',
                            type=os.path.abspath,
                            help='Source directory holding imagery to convert.')
        parser.add_argument('-o', '--dst',
                            type=os.path.abspath,
                            help='Output destination.')
        parser.add_argument('-f', '--out_format')
        parser.add_argument('-s', '--out_suffix')
        parser.add_argument('-d', '--dryrun', action='store_true')
        parser.add_argument('-v', '--verbose', action='store_true')

        args = parser.parse_args()

        # Set up logger
        if args.verbose:
            handler_level = 'DEBUG'
        else:
            handler_level = 'INFO'
        logger = create_logger(__name__, 'sh',
                               handler_level=handler_level)
        
        submit_jobs(args)

