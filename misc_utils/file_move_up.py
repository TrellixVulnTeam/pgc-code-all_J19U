# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 09:26:01 2020

@author: disbr007
Takes files in subdirectories and moves them up to the specified parent directory.
"""

import argparse
import os
import shutil
import time

from tqdm import tqdm

from logging_utils import create_logger


# # Inputs
# parent_dir = r'V:\pgc\data\scratch\jeff\deliverables\4056_jclark\raw'
# move = True
# dryrun = True
# omit_ending = '.zip'


logger = create_logger('file_move_up', 'sh')


def walkdir(folder):
    """Walk through each files in a directory"""
    for dirpath, dirs, files in os.walk(folder):
        for filename in files:
            yield os.path.abspath(os.path.join(dirpath, filename))


def file_move_up(parent_dir, move, omit_ending=None, dryrun=False):
    """
    Moves (or copies) all files in subdirectories of parent_dir up to the level of parent dir.
    Optionally, can copy instead of moving.
    Optionally, can omit a file ending.

    Parameters
    ----------
    parent_dir : os.path.abspath
        Path to the directory to be parsed, and the level to move up to.
    move : BOOLEAN
        True to MOVE, False to Copy.
    dryrun : BOOLEAN
        True to print messages only.
    omit : STR, optional
        A filepath ending to omit. The default is None.

    Returns
    -------
    None.

    """
    total_files = 0
    for filepath in walkdir(parent_dir):
        total_files += 1
        
    with tqdm(total=total_files, unit='files') as pbar:
        for filepath in walkdir(parent_dir):
            if filepath.endswith(omit_ending):
                continue
            # Create the destination path
            basename = os.path.basename(filepath)
            dst = os.path.join(parent_dir, basename)
            pbar.set_postfix(moving=basename, refresh=False)
            pbar.update()
            pbar.write('{} ---> {}'.format(filepath, dst))
            if not dryrun:
                if move:
                    shutil.move(filepath, dst)
                else:
                    shutil.copy2(filepath, dst)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('parent_directory', type=os.path.abspath,
                        help='Path to parent directory to parse, and level to move/copy to.')
    parser.add_argument('--move', action='store_true',
                        help='True to MOVE, False to copy')
    parser.add_argument('--omit_ending', nargs='+',
                        help='Omit files from move if the have this ending.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print commands without running.')
    
    args = parser.parse_args()
    
    file_move_up(parent_dir=args.parent_directory,
                 move=args.move,
                 omit_ending=tuple(args.omit_ending),
                 dryrun=args.dryrun)
