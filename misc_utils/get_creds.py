# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 12:49:36 2019

@author: disbr007
"""
import os
import platform


def get_creds():
    """Get credentials for logging into danco"""
    creds = []

    system = platform.system()
    if system == 'Linux':
        # creds_loc = os.path.join('/mnt', 'pgc', 'data', 'scratch', 'jeff', 'code', 'pgc-code-all', 'config', 'cred.txt')
        creds_loc = os.path.join('pgc-code-all', 'config', 'cred.txt')
    elif system == 'Windows':
        creds_loc = r"C:\code\pgc-code-all\config\cred.txt"
    with open(creds_loc, 'r') as cred:
        content = cred.readlines()
        for line in content:
            creds.append(str(line).strip())

    return tuple(creds)
