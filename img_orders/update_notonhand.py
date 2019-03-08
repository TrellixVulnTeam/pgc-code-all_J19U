# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:33:17 2019

@author: disbr007
Creates two list of catalog ids
-Onhand
-Not onhand
where on hand is defined as at the PGC, NASA, or has been ordered

TODO: Abstract into functions:
    Inputs:
        PGC index
        NASA index
        Ordered ids at text
    
    Functions:
        Read PGC, NASA indexes, return IDs
        Read ordered IDs, return IDs
        Combine all, remove duplicates
        Write onhand, notonhand to text files

    Outputs:
        Onhand ids text file
        Not onhand ids text file
"""

import geopandas as gpd
import pandas as pd
import os

import query_danco

def read_ids(txt_file):
    ids = []
    with open(txt_file, 'r') as f:
        content = f.readlines()
        for line in content:
            ids.append(line.strip())
    return ids

def read_index(index_path, form, layer=1):
    '''reads PGC or NASA index, either as txt/csv or as ONLY feature class in gdb, otherwise layer
    should be specified'''
    if form in ('csv', 'txt'):
        idx = pd.read_csv(index_path)
    elif form == 'fc':
        idx = gpd.read_file(index_path, driver='OpenFileGDB', layer=layer)
    else:
        print('form not recognized: txt, csv, or fc')
    ids = list(idx['CATALOG_ID'])
    ids = [str(x) for x in ids]
    return ids

def write_ids2txt(ids, out_path):
    with open(out_path, 'w') as out_txt:
        for x in ids:
            out_txt.write('{}\n'.format(str(x)))

## IMA Ordered IDs through 3/5/2018 ***Update this to current ordered
all_paths = [
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_1.csv",
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_2.csv"
        ]
all_ordered = []
for tbl in all_paths:
    with open(tbl, 'r') as f:
        content = f.readlines()
        content = [x.strip() for x in content] 
        for x in content:
            all_ordered.append(x)

## Read PGC index     
# Read PGC index into geopandas
#index_path = r"C:\Users\disbr007\pgc_index\pgcImageryIndexV6_2019feb04.gdb"
#index = gpd.read_file(index_path, driver='OpenFileGDB', layer='pgcImageryIndexV6_2019feb04')

# Read text version of master footprint into pandas
pgc_path = r"C:\Users\disbr007\imagery_orders\not_onhand\index.txt"
nasa_path = r"C:\Users\disbr007\imagery_orders\not_onhand\nga_inventory20190219.txt"

index_paths = [pgc_path, nasa_path]
index_ids = []
for p in index_paths:
    ids = read_index(p, 'txt')
    for x in ids:
        index_ids.append(x)

ordered_paths = [
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_1.csv",
        r"C:\Users\disbr007\imagery_orders\not_onhand\all_order_2019march06_2.csv"
        ]

ordered_ids = []
for p in ordered_paths:
    ord_ids = read_ids(p)
    for e in ord_ids:
        ordered_ids.append(e)

onhand_ids = index_ids + ordered_ids
onhand_ids = sorted(onhand_ids)

oh_outpath = r'C:\Users\disbr007\imagery_orders\not_onhand\onhand_ids.txt'
write_ids2txt(onhand_ids, oh_outpath)

## Get stereo not onhand from combining 'stereo_not_onhand_left' and 'stereo_not_onhand_right'
stereo_noh = query_danco.stereo_noh()
# List ids in stereo not_on_hand
stereo_noh_ids = list(stereo_noh['catalogid'])

# Remove all on hand ids from list of not on hand -> this theoretically shouldn't be necessary but is for some reason - talk to CLaire
stereo_noh_clean = set(stereo_noh_ids).difference(onhand_ids)

## Write stereo ids not on hand to list
noh_outpath = r'C:\Users\disbr007\imagery_orders\not_onhand\not_onhand_ids.txt'
write_ids2txt(stereo_noh_clean, noh_outpath)