# -*- coding: utf-8 -*-
"""
Created on Fri Jun  7 09:42:51 2019

@author: disbr007
Gets all ids that have been added to orders from the lists provided to Paul.
"""

import logging
import os, tqdm, argparse, datetime
import pandas as pd

from id_parse_utils import read_ids, write_ids, date_words


#### Logging setup
# create logger
logger = logging.getLogger('ahap_upload')
logger.setLevel(logging.DEBUG)
# create file handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


ordered_ids_path = r'E:\disbr007\imagery_orders\ordered\all_ordered_{}.pkl'.format(date_words(today=True))


def id_order_loc_update():
    '''
    Reads ids from excel sheets, pairing each id with the associated order (directory name)
    '''
    global ordered_ids_path
    # Directory holding sheets of orders - copied from the server location manually
    sheets_dir = r'E:\disbr007\imagery_orders'
#    sheets_dir = r'V:\pgc\data\common\pgc_imagery_orders\NGA'
    
    ## Walk directory and create df of ids and source order
    # Initiate master df to store ids and sources
    all_ids = []
    excel_ext = ['.xls', '.xlsx']
    exception_count = 0
    logger.info('Parsing ordered sheets')
    for root, dirs, files in tqdm.tqdm(os.walk(sheets_dir)):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in excel_ext:
                fpath = os.path.join(root, file)
                try:
                    order = os.path.basename(os.path.dirname(fpath))
                    ctime = os.path.getctime(fpath)
                    dtime = datetime.datetime.fromtimestamp(ctime)
                    df = pd.read_excel(fpath, header=None)
                    ids = df[0]
                    for i in ids:
                        all_ids.append((i, order, dtime))
                except LookupError:
                    exception_count += 1
    all_orders = pd.DataFrame(all_ids, columns=['ids', 'order', 'created'])
    all_orders.to_pickle(ordered_ids_path)
    logger.info('Pickle created at {}'.format(ordered_ids_path))
    ordered_text = r'E:\disbr007\imagery_orders\ordered\all_ordered_{}.txt'.format(date_words(today=True))
    write_ids(list(all_orders['ids']), ordered_text)
    return all_orders


def get_ordered_ids():
    '''
    Returns a list of all ids in an order sheet
    '''
    global ordered_ids_path
    ordered_ids_df = pd.read_pickle(ordered_ids_path)
    return list(ordered_ids_df['ids'])


def lookup_id_order(txt_file, all_orders=None, write_missing=False):
    '''
    takes a txt_file of ids, returns an excel file with the order location of each id
    txt_file: txt file of ids, one per line
    all_orders: df containing ids and order sheets
    '''
    global ordered_ids_path
    if isinstance(all_orders, pd.DataFrame):
        pass
    else:
        all_orders = pd.read_pickle(ordered_ids_path)
        
    txt_ids = read_ids(txt_file)
    ids_loc = all_orders.loc[all_orders['ids'].isin(txt_ids)]
    ids_loc.to_excel(os.path.join(os.path.dirname(txt_file), 'order_sources.xlsx'), index=False)
    
    if write_ids:
        ordered = set(ids_loc.ids)
        missing = [x for x in txt_ids if x not in ordered]
        write_ids(missing, os.path.join(os.path.dirname(txt_file), 'not_in_order.txt'))
    
    return ids_loc



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_ids", type=str, 
                        help="Text file containing ids, one per line.")
    parser.add_argument("--write_missing", action="store_true",
                        help="write ids not in an order to a seperate txt file.")
    parser.add_argument("-u", "--update_orders_source", action="store_true", 
                        help="update the local copy of order sheets before looking up ids.")
    parser.add_argument("--update_only", action="store_true",
                        help="update ordered list files")
    args = parser.parse_args()

    if args.update_only:
        id_order_loc_update()
        
    else:
        # If update flag is specified, update order source .pkl (improve to not reload all, just update new 
        # (date based?)), # else use stored .pkl 
        if args.update_orders_source:
            if args.write_missing:
                lookup_id_order(args.input_ids, id_order_loc_update(), write_missing=True)
            else:
                lookup_id_order(args.input_ids, id_order_loc_update())
        else:
            if args.write_missing:
                lookup_id_order(args.input_ids, write_missing=True)
            else:
                lookup_id_order(args.input_ids)
