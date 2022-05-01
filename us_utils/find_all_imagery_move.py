import argparse
from gettext import find
import glob
import logging
import os
from pathlib import Path
import shutil
from tqdm import tqdm

# from misc_utils.id_parse_utils import parse_filename


logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                              '%(message)s')
logger.setLevel('INFO')
sh = logging.StreamHandler()
sh.setLevel('INFO')
sh.setFormatter(formatter)
logger.addHandler(sh)

# src_dir = '/media/jeff/disbrow5TB/hilgardite/disbr007/umn'
# dest_dir = Path('/media/jeff/disbrow5TB/ms/data/img')
class constants:
    TIF = '.tif'
    NTF = '.ntf'
    NDVI = 'ndvi'
    PANSH = 'pansh'
    MR = 'u16mr3413'
    RF = 'u16rf3413'
    NS = 'u16ns3413'
    

def find_imagery(src_dir, patterns, omit=None):
    logger.debug(f'Searching for files matching {patterns} in {src_dir}...')
    imagery = []
    src_file_count = 0
    for root, dirs, files in tqdm(os.walk(src_dir), desc='searching'):
        for f in files:
            if all([p in f for p in patterns]):
                # Check for omit patterns, skip if found
                if omit is not None and any([op in f for op in omit]):
                    continue
                src_file = Path(root) / f
                src_file_count += 1

                imagery.append(src_file)
                image_file_pattern = f'{str(src_file.parent / src_file.stem)}.*'
                meta_files = glob.glob(image_file_pattern)
                meta_files = [Path(mf) for mf in meta_files]
                imagery.extend(meta_files)
    logger.info(f'Source files found {patterns}: {src_file_count}')
    logger.debug(f'Total files {patterns}: {len(imagery)}')
    return imagery


def move_imagery(imagery, dst_dir, dryrun=False):
    # Move imagery
    
    move_list = []
    for fp in imagery:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        dest_file = dst_dir / fp.name
        if not dest_file.exists():
            move_list.append((fp, dest_file))
            
    logger.info(f'Linking {len(move_list)} files to {dst_dir}...')
    for src_f, dst_f in move_list:
        if dryrun:
            continue
        os.link(src_f, dst_f)



def find_all_imagery_move(src_dir, dst_parent_dir=None, dryrun=False):
    # Locate imagery
    # Raw 
    raw_imagery = find_imagery(src_dir, [constants.NTF])
    # Ortho
    mr_imagery = find_imagery(src_dir, [constants.TIF, constants.MR], omit=[constants.NDVI, constants.PANSH])
    rf_imagery = find_imagery(src_dir, [constants.TIF, constants.RF], omit=[constants.NDVI, constants.PANSH])
    ns_imagery = find_imagery(src_dir, [constants.TIF, constants.NS], omit=[constants.NDVI, constants.PANSH])
    # Deriv
    pansh_imagery = find_imagery(src_dir, [constants.TIF, constants.PANSH], omit=[constants.NDVI])
    ndvi_imagery = find_imagery(src_dir, [constants.TIF, constants.NDVI])
    
    # Move imagery
    dst_parent_dir = Path(dst_parent_dir)
    move_imagery(raw_imagery, dst_dir=dst_parent_dir / 'raw', dryrun=dryrun)
    move_imagery(mr_imagery, dst_dir=dst_parent_dir / 'u16mr3413', dryrun=dryrun)
    move_imagery(rf_imagery, dst_dir=dst_parent_dir / 'u16rf3413', dryrun=dryrun)
    move_imagery(ns_imagery, dst_dir=dst_parent_dir / 'u16ns3413', dryrun=dryrun)
    move_imagery(pansh_imagery, dst_dir=dst_parent_dir / 'pansh', dryrun=dryrun)
    move_imagery(ndvi_imagery, dst_dir=dst_parent_dir / 'ndvi', dryrun=dryrun)
    

# find_all_imagery_move(r'/media/jeff/disbrow5TB/hilgardite/disbr007')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src_dir', required=True)
    parser.add_argument('--dst_dir')
    parser.add_argument('--dryrun', action='store_true')
    
    args = parser.parse_args()
    
    find_all_imagery_move(src_dir=args.src_dir, 
                          dst_parent_dir=args.dst_dir,
                          dryrun=args.dryrun)
