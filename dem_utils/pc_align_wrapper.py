# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import argparse
import os
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger


# INPUTS
# dem1 = r''
# dem2 = r''
# dem3 = r''

# align_dir = r''


def main(dem1, dem2, out_dir):
    """
    Aligns DEMs and writes outputs to out_dir.

    Parameters
    ----------
    dem1 : os.path.abspath
        Path to the reference DEM.
    dem2 : os.path.abspath
        Path to the DEM to translate.
    out_dir : os.path.abspath
        Path to write alignment files to.

    Returns
    -------
    None.

    """
    
    logger = create_logger(os.path.basename(__file__), 'sh')
    
    # PARAMETERS
    dem1_name = os.path.basename(dem1).split('.')
    dem2_name = os.path.basename(dem2).split('.')
    
    
    #### FUNCTION DEFINITION ####
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = proc.communicate()
        print('Output: {}'.format(output))
        print('Err: {}'.format(error))
    
    
    
    #### RUN PC_ALIGN ####
    max_displacement = 10
    threads = 16
    prefix = 'pca_{}_{}'.format(dem1_name, dem2_name)
    
    pca_command = """pc_align --save-transformed-source-points 
                    --max-displacement {} 
                    --threads {} 
                    {} {} 
                    -o {}""".format(max_displacement,
                                    threads,
                                    dem1,
                                    dem2,
                                    os.path.join(out_dir, prefix))
    logger.info('pc_align command:\n'.format(pca_command))
    logger.info(pca_command)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('dem1', type=os.path.abspath,
                        help='Path to the DEM to align to, the reference DEM.')
    parser.add_argument('dem2', type=os.path.abspath,
                        help='Path to the DEM to translate.')
    parser.add_argument('out_dir', type=os.path.abspath,
                        help='Path to write output files to.')
    
    args = parser.parse_args()
    
    dem1 = args.dem1
    dem2 = args.dem2
    out_dir = args.out_dir
    
    main(dem1, dem2, out_dir)
    