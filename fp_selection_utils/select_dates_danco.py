"""
***NOT FINISHED***
Selects features from specified danco layer that fall within a date range
"""

import os, argparse
from query_danco import query_footprint

def dates2sql(d1, d2):
    '''cleans dates to select into sql formatted string
    d1: start date   type: str    eg: '2010-01-31'
    d2: end date     type: str    eg: '2018-10-22'
    '''
    if d1 != None and d2 != None:
        where = "acqdate > '{}' AND acqdate < '{}'".format(args.start, args.end)
    elif d1 == None and d2 != None:
        where = "acqdate < '{}'".format(args.end)
    elif d1 != None and d2 == None:
        where = "acqdate > '{}'".format(args.start)
    else:
        where = None
    return where

## TODO: Export shapefile
## TODO: Make sure date selection works

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layer',
                        type=str, 
                        help="""layer within danco footprint DB to search within. supported layers: 
		'dg_imagery_index_stereo_cc20'
        'dg_imagery_index_all_notonhand_cc20'
        ...
        """)
    parser.add_argument('--start', 
                        type=str,
                        nargs='?',
                        default=None,
                        help="""start date to begin search. e.g. '2010-01-31'""")
    parser.add_argument('--end', 
                        type=str,
                        nargs='?',
                        default=None,
                        help="""end date for search. e.g. '2011-10-22'""")
    args = parser.parse_args()
    where = dates2sql(args.start, args.end)
    selection = query_footprint(args.layer, where=where)
    print('Features selected: {}'.format(len(selection)))