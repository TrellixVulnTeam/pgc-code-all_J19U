# -*- coding: utf-8 -*-
"""
Created on Tue May 21 13:11:35 2019

@author: disbr007
Transfer any files in src and not in dest to dest
"""

import os, shutil, tqdm, argparse


def find_missing_files(src_path, dst_path, use_exts=None):
    '''
    Returns a list of filles that are in the src_path, that are not in the dst, optionally
    limited by a list of extensions provided to 'use_exts'
    '''
#    src_files = os.listdir(src_path)
#    dst_files = os.listdir(dst_path)
    
    src_files = []
    for dirpath, dirnames, fnames in os.walk(src_path):
        for f in fnames:
            src_files.append(os.path.join(dirpath, f))
            
    dst_files = []
    for dirpath, dirnames, fnames in os.walk(dst_path):
        for f in fnames:
            dst_files.append(os.path.join(dirpath, f))
    
    missing_files = [os.path.join(src_path, x) for x in src_files if x not in dst_files]
    
    if use_exts:
        
        def get_ext(f):
            ext = os.path.basename(f).split('.')[1]
            return ext
        
        missing_files = [x for x in missing_files if get_ext(x) in use_exts]
        
    return missing_files
 
    
def copy_missing_files(src_path, dst_path):
    missing_files = find_missing_files(src_path, dst_path)
    for f in tqdm.tqdm(missing_files):
        shutil.copy2(f, dst_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("src_dir", type=str, help="Path to directory of source files. The files you want copied.")
    parser.add_argument("dst_dir", type=str, help="Path to destination directory that 0 or more files from source.")
    parser.add_argument('-v', action='store_true', help="Verbose: print all missing files.")
    
    args = parser.parse_args()
   
    src_dir = os.path.abspath(args.src_dir)
    dst_dir = os.path.abspath(args.dst_dir)
    
    print('Finding missing files...')
    missing = find_missing_files(src_dir, dst_dir)
    print('Missing files found: {}'.format(len(missing)))
    
    if args.v:
        for f in missing:
            print(f)
        
    perform_move = input('Move missing files? [y/n] ')
    
    if perform_move == 'y':
        print("Moving missing files...")
        copy_missing_files(missing, dst_dir)
    
        print('\nMove complete.')
