"""
imagery order selector
"""

import os, argparse
from query_danco import query_footprint

#sql = "acqdate > '2018-12-31'"
#
#selection = query_footprint(layer, where=sql)

def parse_dates(d1, d2):
#    print(d1, d2)
    if d1 != None and d2 != None:
        where = "acqdate > '{}' AND acqdate < '{}'".format(args.start, args.end)
    elif d1 == None and d2 != None:
        where = "acqdate < '{}'".format(args.end)
    elif d1 != None and d2 == None:
        where = "acqdate > '{}'".format(args.start)
    else:
        where = None
    return where

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
    where = parse_dates(args.start, args.end)
#    print(where)
    selection = query_footprint(args.layer, where=where)
    print('Features selected: {}'.format(len(selection)))
    