# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 12:49:36 2019

@author: disbr007
"""

def get_creds(creds_loc=r"C:\code\pgc-code-all\cred.txt"):
    ## Credentials for logging into danco
    creds = []
    with open(creds_loc, 'r') as cred:
        content = cred.readlines()
        for line in content:
            creds.append(str(line).strip())
    
    return tuple(creds)