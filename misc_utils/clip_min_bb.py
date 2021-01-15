import argparse
import os
from pathlib import Path

from gdal_tools import clip_minbb
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')
sublogger = create_logger('gdal_tools', 'sh', 'INFO')

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--rasters', nargs='+', type=os.path.abspath,
                        help='Paths to rasters to clip. Can be multiple'
                             'arguments, a text file of rasters, a '
                             'directory of rasters, in which case "--ext" '
                             'will be used to identify rasters, or a '
                             'combination.')
    parser.add_argument('-o', '--out_dir', type=os.path.abspath,
                        help='Directory to write clipped rasters to.')
    parser.add_argument('-s', '--suffix', type=str,
                        help='Suffix to add to raster names when writing.')
    parser.add_argument('--ext', type=str,
                        help='The extension to identify rasters when '
                             'providing a directory.')

    args = parser.parse_args()

    args.rasters

    # Parse rasters
    process_rasters = []
    for r in args.rasters:
        rp = Path(r)
        if rp.is_file():
            process_rasters.append(r)
        elif rp.is_dir():
            for root, dirs, files in os.walk(r):
                for f in files:
                    if f.endswith(args.ext):
                        process_rasters.append(str(Path(root) / f))
        elif rp.suffix == '.txt':
            with open(r) as src:
                txt_rasters = src.readlines()
            process_rasters.extend(txt_rasters)

    logger.info('Clipping rasters to minimum bounding box:'
                '\n{}'.format('\n'.join(process_rasters)))

    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    clip_minbb(rasters=process_rasters,
               out_dir=args.out_dir,
               out_suffix=args.suffix)