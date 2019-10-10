# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 12:42:09 2019

@author: disbr007
"""

from query_danco import query_footprint

test = query_footprint(layer='scene_dem2', 
#                       db='footprint', 
                       db='dem.dem',
                       instance='tst-sandwich.pgc.umn.edu',
#                       instance='danco.pgc.umn.edu')
                       creds=['pgc_footprint_tst', 'lament@the.fr0zen#walrus'])
#                              
#test2 = query_footprint(layer='dg_imagery_index_all_cc20_7days', 
#                       db='footprint', 
##                       db='dem',
##                       instance='tst-sandwich.pgc.umn.edu',
#                       instance='danco.pgc.umn.edu')
##                       creds=['pgc_footprint_tst', 'lament@the.fr0zen#walrus'])