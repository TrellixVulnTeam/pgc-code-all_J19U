import argparse
import os
from pathlib import Path

from dem_utils import get_aux_file, get_dem_image1_id
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--dems', type=os.path.abspath, nargs='+',
                        help='Path to DEM, DEM(s), or directory holding DEMs.')
    parser.add_argument('-o', '--out_txt', type=os.path.abspath,
                        help='Path to write list of DEM Image1 IDs.')
    parser.add_argument('-ds', '--dem_sfx', default='dem.tif',
                        help='Suffix to locate DEMs by, if directory '
                             'provided.')

    args = parser.parse_args()

    dems = args.dems
    out_txt = args.out_txt
    dem_sfx = args.dem_sfx

    # Get DEMs
    logger.info('Locating DEMs...')
    parse_dems = []
    for d in dems:
        pd = Path(d)
        if pd.is_file():
            if pd.exists():
                parse_dems.append(d)
            else:
                logger.info('File not found: {}'.format(d))
        elif pd.is_dir():
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.endswith(dem_sfx):
                        parse_dems.append(os.path.join(root, f))

    logger.info('DEMs located: {}'.format(len(dems)))
    logger.info('\n{}'.format('\n'.join(parse_dems)))

    logger.info('Locating Image1 IDs...')
    image1_ids = []
    for d in parse_dems:
        meta = get_aux_file(d, 'meta')
        i1id = get_dem_image1_id(meta)
        image1_ids.append(i1id)

    logger.info('Image1 IDs:\n{}'.format('\n'.join(image1_ids)))
    if out_txt:
        logger.info('Writing Image1 IDs to file: {}'.format(out_txt))
        with open(out_txt, 'w') as src:
            src.writelines(image1_ids)
