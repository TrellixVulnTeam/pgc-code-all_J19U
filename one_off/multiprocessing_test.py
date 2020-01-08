# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 12:25:39 2020

@author: disbr007
"""

import time

import multiprocessing as mp
from multiprocessing import Pool


def move_fxn(src, dst):
    print(src,'-->', dst)
    time.sleep(0.1)

num_cpus = mp.cpu_count()
print('CPUs: {}'.format(num_cpus))

srcs = [1,2,3,4,5,6]
dsts = ['a','b','c','d','e','f']

movers = zip(srcs, dsts)

jobs = []

for src, dst in movers:
    p = mp.Process(target=move_fxn, args=(src, dst))
    jobs.append(p)
    p.start()
    
for j in jobs:
    j.join()