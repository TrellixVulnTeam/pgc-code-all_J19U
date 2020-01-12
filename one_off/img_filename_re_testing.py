# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 10:35:27 2020

@author: disbr007
"""


import re


o_f = r'11SEP20224508-P1BS-011782827010_01_P009_u08mr3338'
r_f = r'GE01_20090903231802_1050410004315C00_09SEP03231802-M1BS-011782816010_01_P002'

raw_reg = re.compile('^.{4}_')
ortho_reg = re.compile('^.{13}-')

if re.match(raw_reg, r_f):
    print('raw match')
    
if re.match(ortho_reg, o_f):
    print('ortho match')

if re.match(ortho_reg, r_f):
    print('ortho reg matched raw :(')
    
if re.match(raw_reg, o_f):
    print('raw reg matched ortho :(')