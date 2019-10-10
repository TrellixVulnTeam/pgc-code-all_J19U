# -*- coding: utf-8 -*-
"""
Created on Wed Oct  9 16:59:43 2019

@author: disbr007
"""

from osgeo import gdal
import os
import subprocess


src_dir = r'V:\pgc\data\scratch\jeff\elev\tandemx\tdm90_central_russia'

dems = []

for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith('DEM.tif'):
            f_p = os.path.join(root, f)
            dems.append(f_p)
            
## Mosaic relevant tiles
def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    print('Output: {}'.format(output))
    print('Err: {}'.format(error))

dems_str = ' '.join(dems)

command = 'gdalbuildvrt mosaic.vrt {}'.format(dems_str)
run_subprocess(command)