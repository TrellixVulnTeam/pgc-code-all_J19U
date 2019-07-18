# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 16:20:46 2019

@author: disbr007
Get all ids from mfp by looping through slices of mfp
"""

import os, tqdm
from id_parse_utils import write_ids
from select_ids_pgc_index import mfp_subset


def main(field_of_int):
    '''
    Loops through master footprint subset layers and extracts the field of interest values
    field_of_int: field in the master footprint to find. e.g. 'catalog_id'
    '''
    values = []
    for layer in tqdm.tqdm(mfp_subset(-180, -90, 180, 90)):
        layer_values = list(set(layer[field_of_int]))
        for each_id in layer_values:
            values.append(each_id)

    write_ids(set(values), os.path.join(r'C:\pgc_index', '{}.txt'.format(field_of_int)))


if __name__ == '__main__':
    main()