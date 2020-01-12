# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 11:19:29 2020

@author: disbr007
"""

import os
import shutil
import time

from threading import Thread
from multiprocessing import Pool


def fxn(src, dst):
    shutil.copy2(src, dst)
    time.sleep(5)
    return 'success'


prj_dir = r'C:\temp\mp_test'
srcs = [os.path.join(prj_dir, 'src_master', f) for f in os.listdir(os.path.join(prj_dir, 'src_master'))]
dsts = [os.path.join(prj_dir, 'dst_master', f) for f in os.listdir(os.path.join(prj_dir, 'src_master'))]

x = zip(srcs, dsts)

# threads = []
# for src, dst in x:
#     t = Thread(target=fxn, args = (src, dst,))
#     t.start()

p = Pool(processes=4)
results = p.map(fxn, x)

p.close()
p.join()
