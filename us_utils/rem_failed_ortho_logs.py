# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 10:57:46 2020

@author: disbr007
"""

import argparse
import os
from tqdm import tqdm

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def remove_failed_logs(log_dir, dryrun=False):
    failed_logs = []
    for f in os.listdir(log_dir):
        with open(os.path.join(log_dir, f), 'r') as lf:
            content = lf.read()
            if 'Processing failed: ' in content:
                failed_logs.append(os.path.join(log_dir, f))
    
    logger.info('Log files to be deleted: {}'.format(len(failed_logs)))
    
    if not dryrun:
        for f in tqdm(failed_logs):
            os.remove(f)

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_directory', type=os.path.abspath,
                        help='Directory to parse for log files from failed jobs.')
    parser.add_argument('-d', '--dryrun', action='store_true')
    
    args = parser.parse_args()
    
    remove_failed_logs(args.input_directory, args.dryrun)
    
    