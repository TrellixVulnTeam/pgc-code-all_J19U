# -*- coding: utf-8 -*-
"""
Created on Tue May 12 12:14:25 2020

@author: disbr007
"""

import argparse
import os

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'DEBUG')


def matching_files(directory, recursive=True, 
                   starts=None, ends=None,
                   contains=None, ext=None):
    logger.info('Scanning {} for files matching filters...'.format(directory))
    logger.debug("""Filters:
                 starts: {}
                 ends: {}
                 contains: {}
                 ext: {}
                 recursive: {}""".format(starts, ends, contains, ext, recursive))
    # Create file list
    match_fullpaths = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            if starts:
                files = [f for f in files if f.startswith(starts)]
            if ends:
                files = [f for f in files if os.path.splitext(f)[0].endswith(ends)]
            if contains:
                files = [f for f in files if contains in f]
            if ext:
                files = [f for f in files if f.endswith(ext)]
            
            # Add full paths to matches to master list
            match_fullpaths.extend([os.path.join(root, f) for f in files])
            
    else:
        files = [f for f in os.listdir(directory) 
                 if os.path.isfile(os.path.join(directory, f))]
        
        if starts:
            files = [f for f in files if f.startswith(starts)]
        if ends:
            files = [f for f in files if os.path.splitext(f)[0].endswith(ends)]
        if contains:
            files = [f for f in files if contains in f]
        if ext:
            files = [f for f in files if f.endswith(ext)]
        
        # Add full paths to master list
        match_fullpaths.extend([os.path.join(directory, f) for f in files])
        
    logger.info('Found matching files: {}'.format(len(match_fullpaths)))
    
    return match_fullpaths
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_directory', type=os.path.abspath,
                        help='Path to directory to search.')
    parser.add_argument('-o', '--out_txt', type=os.path.abspath,
                        help='Path to write list of files to.')
    parser.add_argument('-s', '--starts_with', type=str,
                        help='Filename starts with filter.')
    parser.add_argument('-e', '--ends_with', type=str,
                        help='Filename ends with filter -- extension not included.')
    parser.add_argument('-c', '--contains', type=str,
                        help="Filename contains filter.")
    parser.add_argument('-x', '--ext', type=str,
                        help="""File extension filter -- can also be used for suffix+ext,
                                I.e.: 'pansh.tif'""")
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Flag to search recursively through input_directory.')
    
    args = parser.parse_args()
    
    mf = matching_files(directory=args.input_directory,
                        recursive=args.recursive,
                        starts=args.starts_with,
                        ends=args.ends_with,
                        contains=args.contains,
                        ext=args.ext)
    
    with open(args.out_txt, 'w') as out:
        for f in mf:
            out.write(f)
            out.write('\n')
    