# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 21:53:45 2020

@author: disbr007
"""

import os
import subprocess
from subprocess import PIPE


# INPUTS
dem1 = r''
dem2 = r''
dem3 = r''

align_dir = r''


#### FUNCTION DEFINITION ####
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    output, error = proc.communicate()
    print('Output: {}'.format(output))
    print('Err: {}'.format(error))




