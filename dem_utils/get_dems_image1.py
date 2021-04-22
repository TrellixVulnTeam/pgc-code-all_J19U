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
    parser.add_argument('-a', '--append_ids', action='store_true',
                        help='Use to append IDs to out_txt, if it exists.')
    parser.add_argument('-ds', '--dem_sfx', default='dem.tif',
                        help='Suffix to locate DEMs by, if directory '
                             'provided.')

    args = parser.parse_args()

    dems = args.dems
    out_txt = args.out_txt
    append_ids = args.append_ids
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
        if not Path(out_txt).parent.exists():
            os.makedirs(Path(out_txt).parent)
        out_txt = Path(out_txt)
        if out_txt.exists() and append_ids:
            write_mode = 'a'
        elif out_txt.exists() and not append_ids:
            logger.warning('Overwriting {}'.format(out_txt))
            write_mode = 'w'
        else:
            write_mode = 'w'
        logger.info('Writing Image1 IDs to file: {}'.format(out_txt))
        with open(out_txt, write_mode) as src:
            for i in image1_ids:
                src.write('{}\n'.format(i))
            # src.writelines(image1_ids)