# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 07:50:03 2019

@author: disbr007
"""
import argparse
import logging
import os

from id_parse_utils import write_ids
from selection_utils.query_danco import query_footprint


def main(args):
    MFP_PATH = args.mfp_path
    CATALOG_ID = args.field_of_int
    IDS_OUT_DIR = args.ids_out_dir

    ID_OUT_NAME = os.path.basename(MFP_PATH).split('.')[0]
    ID_OUT_BASENAME = '{}_{}.txt'.format(ID_OUT_NAME, args.field_of_int)
    if not IDS_OUT_DIR:
        IDS_OUT_PATH = os.path.join(os.path.dirname(MFP_PATH), ID_OUT_BASENAME)   
    else:
        IDS_OUT_PATH = os.path.join(IDS_OUT_DIR, ID_OUT_BASENAME)
        
    logging.info('Reading IDs...')
    pgc_cid_fp = query_footprint('pgc_imagery_catalogids', 
                                 table=True, 
                                 columns=[CATALOG_ID])
    
    cids = list(pgc_cid_fp[CATALOG_ID])
    
    logging.info('Writing IDs to {}...'.format(IDS_OUT_PATH))
    write_ids(cids, IDS_OUT_PATH)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--mfp_path', type=str, help='Path to master footprint.')
    parser.add_argument('--ids_out_dir', type=os.path.abspath,
                        help='Directory to write text file of IDs to.')
    parser.add_argument('--field_of_int', type=str, default='catalog_id',
                        help='Field to capture to text')
    
    args = parser.parse_args()

    main(args)    
