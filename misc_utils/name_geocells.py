# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 13:15:06 2020

@author: disbr007
"""

import os

import numpy as np
import geopandas as gpd


# prj_path = r'E:\disbr007\general\geocell'

geocells_path = r'E:\disbr007\general\geocell\one_degree_geocell.shp'

def name_cell(poly):
    minx, miny, maxx, maxy = poly.bounds
    ulx, uly = round(minx), round(maxy)
    if ulx < 0:
        x_dir = 'w'
    else:
        x_dir = 'e'
    if uly < 0:
        y_dir = 's'
    else:
        y_dir = 'n'

    name = '{}{}{}{}'.format(y_dir, abs(uly), x_dir, abs(ulx))

    return name

gc = gpd.read_file(geocells_path)
gc['name'] = gc.geometry.apply(lambda x: name_cell(x))


gc.to_file(r'E:\disbr007\general\geocell\one_degree_geocell_named.shp')