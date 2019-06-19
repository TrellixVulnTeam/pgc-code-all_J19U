# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 10:02:23 2019

@author: disbr007
"""

from id_parse_utils import combine_ids
import argparse, os


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('id_files', nargs='+', default='*',
                        help='The id files to combine.')
    parser.add_argument('-w', '--write_path', 
                        help='The path to write the combined list. Defaults to parent directory of first list')
    
    args = parser.parse_args()
    
    if args.write_path:
        write_path = args.write_path
    else:
        write_path = os.path.join(os.path.dirname(args.id_files[0]), 
                                                  '{}_combined.txt'.format(os.path.basename(args.id_files[0].split('.')[0])))
    
    id_files = args.id_files

    for i, each in enumerate(id_files):
        if os.path.exists(each):
            pass
        else:
            try:
                new_path = os.path.abspath(each)
                if os.path.exists(new_path):
                    id_files[i] = new_path
                else:
                    print('Cannot locate file {}'.format(each))
            except Exception as e:
                print(e)

    combine_ids(*id_files, write_path=write_path)