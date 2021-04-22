import argparse
import os
import sys

sys.path.insert(1, r'C:\code\pgc-code-all')
from misc_utils.rio_utils import fill_internal_nodata
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--image', type=os.path.abspath)
    parser.add_argument('-o', '--out', type=os.path.abspath)
    parser.add_argument('-a', '--aoi', type=os.path.abspath)

    args = parser.parse_args()

    logger.info('Filling internal NoData...')
    fill_internal_nodata(img=args.image, out=args.out, aoi=args.aoi)
    logger.info('Done.')
