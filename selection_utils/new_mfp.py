# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27

@author: disbr007
"""

import argparse
import logging.config
import os
import subprocess
from subprocess import PIPE
import zipfile

from misc_utils.logging_utils import LOGGING_CONFIG


handler_level = 'DEBUG'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=False)
    # proc.wait()
    output, error = proc.communicate()
    logger.info('Output: {}'.format(output.decode()))
    logger.info('Err: {}'.format(error.decode()))


def main(MFP_PATH):
    TXT_LOC = r'C:\code\pgc-code-all\config\pgc_index_path.txt'
    GET_IDS_PY = r'C:\code\pgc-code-all\misc_utils\mfp_ids.py'
    pgc_dir = r'C:\pgc_index'
    # pgc_dir = os.path.dirname(MFP_PATH)
    gdb_name = os.path.basename(MFP_PATH)[:-4]  # with .gdb
    gdb_basename = gdb_name.split('.')[0]  # just the name

    gdb_fp = os.path.join(pgc_dir, gdb_name)  # full path to gdb
    mfp_layer = os.path.join(gdb_fp, gdb_basename)  # full path to layer

    logger.info('Unzipping to {}...'.format(gdb_fp))
    with zipfile.ZipFile(MFP_PATH, 'r') as zip_ref:
        zip_ref.extractall(gdb_fp)

    # mfp_name = os.path.basename(MFP_PATH)
    IDS_LOC = os.path.join(os.path.dirname(TXT_LOC), '{}_catalog_id.txt'.format(gdb_name.replace('.gdb', '')))
    TXT_DIR = os.path.dirname(TXT_LOC)

    logger.info('Updating text file of catalog_ids...')
    cmd = 'python {} --mfp_path {} --ids_out_dir {}'.format(GET_IDS_PY, MFP_PATH, TXT_DIR)
    logger.debug('Calling command:\n{}'.format(cmd))
    run_subprocess(cmd)

    logger.info('Updating locations of master footprint and catalog_ids.txt...')

    with open(TXT_LOC, 'w') as txt:
        txt.write(mfp_layer)
        txt.write('\n')
        txt.write(IDS_LOC)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('mfp_path', type=os.path.abspath,
                        help="""Path to new master footprint gdb.
                                Layer name need not be specified - created automatically.""")

    args = parser.parse_args()

    MFP_PATH = args.mfp_path

    main(MFP_PATH)
