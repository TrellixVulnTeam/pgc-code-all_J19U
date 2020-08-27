import argparse
from pathlib import Path

import os
import re
import glob

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


# dems_dir = r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\dems'

def sceneids_from_dems_dir(dems_dir, multispectral=False):
    dems_dir = Path(dems_dir)
    meta_files = dems_dir.rglob('*meta.txt')
    # meta_files = glob.glob(os.path.join(dems_dir, '*meta.txt'), recursive=True)

    # logger.info('Meta files found: {}'.format(len(meta_files)))
    #
    reg = re.compile(r"Image \d=(.*)\n")

    sids = []
    for mf in meta_files:
        with open(mf, 'r') as src:
            content = src.readlines()
            for line in content:
                match = reg.match(line)
                if match:
                    sid_path = match.groups()[0]
                    dem_sid = os.path.splitext(os.path.basename(sid_path))[0]
                    if dem_sid.endswith('temp'):
                        dem_sid = dem_sid[:-5]
                    sids.append(dem_sid)

    if multispectral:
        logger.info('Adding multispectral scene IDs...')
        ms_sids = [s.replace('P1BS', 'M1BS') for s in sids
                   if s.startswith('WV02', 'WV03', 'QB', 'GE01')]
        sids.extend(ms_sids)

    return set(sids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--dems_dir', type=os.path.abspath,
                        help='Directory with DEMs and associated *meta.txt files.')
    parser.add_argument('-o', '--out_sid_list', type=os.path.abspath,
                        help="Path to write list of IDs to.")
    parser.add_argument('-ms', '--multispectral', action='store_true',
                        help='Add multispectral IDs by substituting M1BS for P1BS.')

    args = parser.parse_args()

    dems_dir = args.dems_dir
    out_sid_list = args.out_sid_list

    logger.info('Reading meta files from directory: {}'.format(dems_dir))
    sids = sceneids_from_dems_dir(dems_dir=dems_dir)

    logger.info('Scene IDs found: {}'.format(len(sids)))

    logger.info('Writing to file: {}'.format(out_sid_list))
    with open(out_sid_list, 'w') as src:
        for sid in sids:
            src.write(sid)
            src.write('\n')
