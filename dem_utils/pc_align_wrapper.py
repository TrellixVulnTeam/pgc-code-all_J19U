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
                                os.path.join(align_dir, prefix))
