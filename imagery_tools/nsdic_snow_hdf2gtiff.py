# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 19:47:32 2020

@author: disbr007
"""
import argparse
import os
import re
import subprocess
from subprocess import PIPE
import sys

from misc_utils.logging_utils import LOGGING_CONFIG, create_logger
from osgeo import gdal


#### Function definition
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        logger.info(line.decode())
    proc_err = ""
    for line in iter(proc.stderr.readline, b''):
        proc_err += line.decode()
    if proc_err:
        logger.info(proc_err)
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


logger = create_logger(__name__, 'sh',
                           handler_level='INFO')


def main(args):
    hdf = args.input_hdf
    output_directory = args.output_directory
    output_filepath = args.output_filepath
    overwrite = args.overwrite
    
    if output_directory and not output_filepath:
        hdf_name = os.path.basename(os.path.splitext(hdf)[0])
        output_filepath = os.path.join(output_directory, '{}.tif'.format(hdf_name))
    if os.path.exists(output_filepath) and not overwrite:
        logger.warning('Output file exists:\n{}\n...and overwrite not specified, quitting...'.format(output_filepath))
        sys.exit()
        
    info = gdal.Info(hdf)
    
    sub_ds_one_regex = re.compile(r'SUBDATASET_1_NAME=(.*)\n')
    hdf_str = sub_ds_one_regex.search(info)
    hdf_lyr = hdf_str.groups()[0]
    
    no_data = 254

    cmd = """gdal_translate -co COMPRESS=LZW -of GTiff -ot Byte -a_nodata {} {} {}""".format(no_data, hdf_lyr, output_filepath)
    
    run_subprocess(cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--input_hdf', type=os.path.abspath)
    parser.add_argument('-od', '--output_directory', type=os.path.abspath)
    parser.add_argument('-o', '--output_filepath', type=os.path.abspath)
    parser.add_argument('--overwrite', action='store_true')
    
    args = parser.parse_args()

    main(args)
    # print(args.input_hdf)