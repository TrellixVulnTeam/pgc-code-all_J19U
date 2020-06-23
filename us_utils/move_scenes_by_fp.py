import argparse
import time
import glob
import os
import re
import shutil

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

# src_dir = r'V:\pgc\data\scratch\jeff\deliverables\4228_bjones_ak\utm_fps'
# dst_par_dir = r'V:\pgc\data\scratch\jeff\deliverables\4228_bjones_ak\raw_utms'
# fp_ext = 'shp'
# src_field = 'O_FILEPATH'
# # Dir from which fp.py was run (prefix path in src_field)
# imagery_base_dir = r'V:\pgc\data\scratch\jeff\deliverables\4228_bjones_ak'
# link = True

def convert_path(path):
    s = re.split(r'/|\\', path)
    s = [i for i in s if i]
    converted = os.sep.join(s)

    return converted

def move_scenes_by_fps(src_dir, dst_par_dir, imagery_base_dir,
                       fp_ext='shp', src_field='O_FILEPATH',
                       link=False):
    # Iterate over footprints
    all_moves = []
    for fp_bn in os.listdir(src_dir):
        if not fp_bn.endswith(fp_ext):
            continue
        fp_p = os.path.join(src_dir, fp_bn)

        # Read in footprint
        logger.info('Loading footprint: {}'.format(fp_bn))
        fp = gpd.read_file(fp_p)
        logger.info('Records found: {}'.format(len(fp)))
        fp[src_field] = fp[src_field].apply(lambda x: convert_path(x))
        # fp[src_field] = fp[src_field].str.replace(r'/', os.path.sep)
        # Get src filepaths
        fp_src_tifs = fp[src_field].apply(lambda x: os.path.join(imagery_base_dir, x))
        fp_srcs = []
        for tif in fp_src_tifs:
            # Get all files that match name (drop extension)
            scene_files = glob.glob('{}*'.format(os.path.splitext(tif)[0]))
            fp_srcs.extend(scene_files)

        # Create dst filepaths
        fp_name = os.path.splitext(fp_bn)[0]
        dst_dir = os.path.join(dst_par_dir, fp_name)

        # Create src, dst tuples
        fp_moves = [(src, os.path.join(dst_dir, os.path.basename(src))) for src in fp_srcs]
        all_moves.extend(fp_moves)

    # Perform moves
    pbar = tqdm(total=len(all_moves), desc='Copying files')
    for (s, d) in all_moves:
        if os.path.exists(d):
            pbar.write('Destination exists, skipping: {}'.format(s))
            continue
        if not os.path.exists(os.path.dirname(d)):
            os.makedirs(os.path.dirname(d))
        if link:
            pbar.write('Linking: {} -> {}'.format(s, d))
            # time.sleep(0.1)
            os.symlink(s, d)
        else:
            pbar.write('Copying: {} -> {}'.format(s, d))
            # time.sleep(0.1)
            shutil.copy(s, d)
        pbar.update(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-sd', '--src_dir', type=os.path.abspath,
                        help='Path to directory holding footprints to parse.')
    parser.add_argument('-dpd', '--dst_par_dir', type=os.path.abspath,
                        help="""Parent directory to move scenes to. Subdirs will be created
                                corresponding to each footprint filename.""")
    parser.add_argument('-ibd', '--imagery_base_dir', type=os.path.abspath,
                        help='Path to directory upon which relative path in src_fld is added.')
    parser.add_argument('-l', '--link', action='store_true',
                        help='Create symlinks rather than actually copying.')
    parser.add_argument('-sf', '--src_fld', type=str, default='O_FILEPATH',
                        help='The name of the field holding relative filepaths to imagery.')
    parser.add_argument('-fe', '--fp_ext', type=str, default='shp',
                        help='The extension of the footprint files.')

    args = parser.parse_args()

    src_dir = args.src_dir
    dst_par_dir = args.dst_par_dir
    imagery_base_dir = args.imagery_base_dir
    link = args.link
    src_field = args.src_fld
    fp_ext = args.fp_ext

    move_scenes_by_fps(src_dir=src_dir, dst_par_dir=dst_par_dir, imagery_base_dir=imagery_base_dir,
                       link=link, fp_ext=fp_ext, src_field=src_field)

    logger.info('Done.')