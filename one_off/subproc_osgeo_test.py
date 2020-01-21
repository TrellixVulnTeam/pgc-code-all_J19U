# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 22:18:48 2020

@author: disbr007
"""

import subprocess
from subprocess import PIPE

cmd = ['echo begin',
       # r'C:\OSGeo4W64\OSGeo4W.bat',
       # r'C:\OSGeo4W64\OTB-6.6.1-Win64\OTB-6.6.1-Win64\otbenv.bat',
       # r'otbcli_LargeScaleMeanShift']
       'echo test']

cmd = '; '.join([c for c in cmd])
def call_cmd(cmd):
    # p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    p = subprocess.check_output(cmd, shell=True)
    # stdout, stderr = p.communicate()
    
    for line in p.strip().decode().splitlines():
        print(line)
    # print(p.returncode)
    # for line in stdout.strip().decode().splitlines():
    #     print(line)
    # for line in stderr.strip().decode().splitlines():
    #     print(line)
    return p
        

p = call_cmd(cmd)

# cmd = ['gdal_translate']

# call_cmd(cmd)