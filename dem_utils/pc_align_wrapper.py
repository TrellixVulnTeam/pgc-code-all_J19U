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
from misc_utils.RasterWrapper import Raster


# INPUTS
dem1 = r'V:\pgc\data\scratch\jeff\ms\dems\clip\WV02_20130629_1030010023174900_103001002452E500_seg2_2m_dem_clip.tif'
dem2 = r'V:\pgc\data\scratch\jeff\ms\dems\clip\WV02_20170410_1030010067C5FE00_1030010068B87F00_seg1_2m_dem_clip.tif'
# dem3 = r''

out_dir = r'V:\pgc\data\scratch\jeff\ms\dems\pca'


def main(dem1, dem2, out_dir, verbose=False):
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
    if verbose:
        handler_level = 'DEBUG'
    else:
        handler_level = 'INFO'
    logger = create_logger(os.path.basename(__file__), 'sh',
                           handler_level=handler_level)
    
    # PARAMETERS
    dem1_name = os.path.basename(dem1).split('.')[0][:12]
    dem2_name = os.path.basename(dem2).split('.')[0][:12]
    
    
    #### FUNCTION DEFINITION ####
    def run_subprocess(command):
        proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = proc.communicate()
        print('Output: {}'.format(output))
        print('Err: {}'.format(error))
    
    
    #### GET INFO ABOUT DEMS ####
    dem1 = Raster(dem1)
    width = dem1.pixel_width
    height = dem1.pixel_height
    res = (abs(width) + abs(height)) / 2
    nodata = dem1.nodata_val
    dem1 = None
    
    
    #### PC_ALIGN ####
    max_displacement = 10
    threads = 16
    prefix = '{}'.format(dem1_name)
    
    pca_command = """pc_align --save-transformed-source-points 
                    --max-displacement {} 
                    --threads {} 
                    --compute-translation-only
                    -o {}
                    {} {} 
                    """.format(max_displacement,
                               threads,
                               os.path.join(out_dir, prefix),
                               dem1,
                               dem2)

    logger.info('pc_align command:\n{}'.format(pca_command))
    # run_subprocess(pca_command)
    
    log_file = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if '-log-pc_align' in f][0]

    with open(log_file, 'r') as lf:
        content = lf.readlines()
        trans_info = 'Translation information:\n'
        for line in content:
            if 'North-East-Down' in line or 'magnitude' in line:
                relevent = '{}\n'.format(line.split('Translation vector')[1])
                relevent = ' '.join(relevent.split('Vector3'))
                trans_info += relevent
        logger.info(trans_info)
    
    
    #### POINT2DEM ####
    out_name = '{}_{}'.format(dem1_name, dem2_name)
    trans_source = '{}-trans_source.tif'.format(prefix)
    p2d_command = """point2dem 
                    --threads {}
                    --nodata-value {}
                    -s {}
                    -o {}
                    {}""".format(threads, nodata, res, out_name, trans_source)
                    
    logger.info('point2dem:\n{}'.format(p2d_command))
                    
    
main(dem1, dem2, out_dir, verbose=True)


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser()
    
#     parser.add_argument('dem1', type=os.path.abspath,
#                         help='Path to the DEM to align to, the reference DEM.')
#     parser.add_argument('dem2', type=os.path.abspath,
#                         help='Path to the DEM to translate.')
#     parser.add_argument('out_dir', type=os.path.abspath,
#                         help='Path to write output files to.')
#     parser.add_argument('-v', '--verbose', action='store_true',
#                         help='Set logging to DEBUG')
    
#     args = parser.parse_args()
    
#     dem1 = args.dem1
#     dem2 = args.dem2
#     out_dir = args.out_dir
#     verbose = args.verbose
    
#     main(dem1, dem2, out_dir, verbose=verbose)
    