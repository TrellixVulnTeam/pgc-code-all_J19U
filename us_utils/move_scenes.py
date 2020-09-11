import argparse
import os
from pathlib import Path
import shutil

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

footprint_p = r'E:\disbr007\UserServicesRequests\Projects\bjones\4300_bjones_ak\selected_scenes.shp'
aoi_p = r''
src_par_dir = Path(r'E:\disbr007\UserServicesRequests\Projects\bjones\4300_bjones_ak\raw')
dst_par_dir = Path(r'E:\disbr007\UserServicesRequests\Projects\bjones\4300_bjones_ak\scratch')

opf = 'strip_id'
opfs = ['catalog_id', 'strip_id']

# Constants
f_sid = 'scene_id'
f_scene_files = 'scene_files'
tm_copy = 'copy'
tm_link = 'link'


def move_scene_files(generator_obj, dst_par_dir, opf_values, tm=tm_copy, dryrun=False):
    for f in generator_obj:
        dst_dir = dst_par_dir
        for ov in opf_values:
            dst_dir = dst_dir / ov
        logger.debug('Copying {} -> {}'.format(f, dst_dir))
        if not dryrun:
            if not dst_dir.exists():
                os.makedirs(dst_dir)
            if tm == tm_copy:
                shutil.copy2(f, dst_dir)
            elif tm == tm_link:
                os.link(f, dst_dir)


def move_scenes(footprint_p, src_par_dir, dst_par_dir, opfs, tm):
    # Read footprint
    logger.info('Reading footprint of scenes to move.')
    footprint = gpd.read_file(footprint_p)
    logger.info('Scenes found: {}'.format(len(footprint)))

    # Find scene files - puts a list of scene files into each row
    logger.info('Finding associated scene files...')
    footprint[f_scene_files] = footprint[f_sid].apply(lambda x: src_par_dir.rglob('{}*'.format(x)))

    # Move scene files
    logger.info('Moving scene files...')
    pbar = tqdm(footprint.iterrows(), total=len(footprint))
    for i, row in pbar:
        pbar.set_description("Moving scene files for: {}".format(row[f_sid]))
        move_scene_files(row[f_scene_files],
                         dst_par_dir=dst_par_dir,
                         opf_values=[row[opf] for opf in opfs],
                         tm=tm,
                         dryrun=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_footprint', type=os.path.abspath,
                        help='Path to footprint of files to move.')
    parser.add_argument('-s', '--src_directory', type=os.path.abspath,
                        help='The directory where the imagery currently is.')
    parser.add_argument('-d', '--dst_directory', type=os.path.abspath,
                        help='The directory to move to.')
    parser.add_argument('--opfs', type=str, nargs='+',
                        help='The field(s) to create subdirectories based on, '
                             'within dst_directory.')
    parser.add_argument('-tm', choices=[tm_copy, tm_link], default=tm_copy,
                        help='Method of copying files.')
    parser.add_argument('--dryrun', action='store_true')

    args = parser.parse_args()

    move_scenes(footprint_p=args.input_footprint,
                src_par_dir=args.src_directory,
                dst_par_dir=args.dst_directory,
                opfs=args.opfs,
                tm=args.tm,
                dryrun=args.dryrun)
