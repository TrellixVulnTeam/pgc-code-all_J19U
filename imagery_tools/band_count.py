import argparse
import os

from osgeo import gdal

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def count_bands(raster):
    src = gdal.Open(raster)
    if src is not None:
        count = src.RasterCount

    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--rasters', type=os.path.abspath,
                        help='Path to raster or directory of rasters to get band counts for.')
    parser.add_argument('-e', '--extensions', nargs='+', default=['tif'],
                        help='Extensions of rasters to get band counts for.')
    parser.add_argument('-s', '--skip_strings', nargs='+',
                        help='Skip raster if path includes any of these strings.')
    parser.add_argument('-k', '--keep_strings', nargs='+',
                        help='Parse only rasters containing these strings.')
    
    args = parser.parse_args()

    rasters = args.rasters
    extensions = args.extensions
    skip_strings = args.skip_strings
    keep_strings = args.keep_strings

    # Create list of rasters to parse
    if os.path.isdir(rasters):
        parse_rasters = [os.path.join(rasters, r) for r in os.listdir(rasters)]
        if extensions:
            parse_rasters = [r for r in parse_rasters if r.endswith(tuple(extensions))]
        if keep_strings:
            parse_rasters = [r for r in parse_rasters if any(k in r for k in keep_strings)]
    elif os.path.isfile(rasters):
        parse_rasters = [rasters]

    # Ensure all rasters exist
    all_exist = any([os.path.exists(r) for r in parse_rasters])
    if not all_exist:
        logger.warning('At least one raster path provided does not exist.')
        missing = [r for r in parse_rasters if not os.path.exists(r)]
        logger.warning('Could not find rasters:\n{}'.format('\n'.join(missing)))
        parse_rasters = [r for r in parse_rasters if os.path.exists(r)]

    for r in sorted(parse_rasters):
        count = count_bands(r)
        logger.info('Band count for {}: {}'.format(os.path.basename(r), count))
