"""
imagery order selector
"""

import os, argparse
from query_danco import query_footprint

#layer = 'dg_imagery_index_stereo_cc20'
#sql = "acqdate > '2018-12-31'"
#
#selection = query_footprint(layer, where=sql)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('layer', type=str, 
		help="""layer within danco footprint DB to search within. e.g. 
		'dg_imagery_index_stereo_cc20;'""")
	parser.add_argument('date_range', type=str, 
		help="""date range to search. e.g. '2017-01-19 : 2019-01-21'
		or '> 2018', or '< 2015'""")
	args = parser.parse_args()
	selection = query_footprint(args.layer, where=args.date_range)
        print(len(selection))
