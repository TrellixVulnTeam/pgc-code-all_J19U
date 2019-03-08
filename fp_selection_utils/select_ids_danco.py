# -*- coding: utf-8 -*-
"""
Created on Thu Mar  7 09:31:11 2019

@author: disbr007
Exports shapefile of selected IDs from specified danco layer
"""

import pandas as pd
import geopandas as gpd
import os, argparse

from query_danco import query_footprint

def read_ids(txt_file):
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            ids.append(line.strip())
    return ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('text_file',
                        type=str,
                        help=
                        """The file containing catalog ids (one per line) to select from 
                        danco layer"""
                        )
    parser.add_argument('layer',
                        type=str,
                        help=
                        """The layer with danco footprint DB to select from. 
                        eg: 'dg_imagery_index_stereo_cc20'"""
                        )
    args = parser.parse_args()
    layer = query_footprint(args.layer)
    ids = read_ids(args.text_file)
    selection = layer[layer.catalogid.isin(ids)]