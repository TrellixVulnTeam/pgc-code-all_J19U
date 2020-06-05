# -*- coding: utf-8 -*-
"""
Created on Tue May 26 15:31:23 2020

@author: disbr007
"""

import os

path_env = [p for p in os.environ['PATH'].split(';')]

bad_paths = [p for p in path_env if not os.path.exists(p)]

print('Bad paths: ')
print('\n'.join(bad_paths))

