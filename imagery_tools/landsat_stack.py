# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 20:10:23 2020

@author: disbr007
"""

import os
import logging
import logging.config
import subprocess

from misc_utils.logging_utils import LOGGING_CONFIG


handler_level = 'DEBUG'
logging.config.dictConfig(LOGGING_CONFIG(handler_level))
logger = logging.getLogger(__name__)


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # proc.wait()
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    if error is not None:
        logger.debug('Err: {}'.format(error.decode()))
    

SCENE_DIR = r'E:\disbr007\umn\ms\imagery\LE070580082014071801T1-SC20200204224358'

bands = [os.path.join(SCENE_DIR, band) for band in os.listdir(SCENE_DIR) if 'band' in band]
out_stack = os.path.join(SCENE_DIR, '{}.tif'.format(bands[0][:-10]))


gdal_merge = r'C:\anaconda\envs\ggs\Scripts\gdal_merge.py'
cmd = """python {} -separate -o {} {}""".format(gdal_merge, out_stack, ' '.join(bands))


run_subprocess(cmd)

