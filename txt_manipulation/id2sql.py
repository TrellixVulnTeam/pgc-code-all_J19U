# -*- coding: utf-8 -*-
"""
Created on Wed Nov 28 11:39:32 2018

@author: disbr007
"""
import os
import argparse

def ids2sql(txt_file):
	proj_path = os.path.dirname(txt_file)
	proj_name = os.path.splitext(os.path.basename(txt_file))[0]
	print(proj_name)
	content = []
	with open(txt_file, 'r') as f:
		lines = f.readlines()
		for line in lines:
			print(line)
			content.append("'{}'".format(line.strip()))
	out_string = ', '.join(content)
	
	with open(os.path.join(proj_path, '{}_sql.txt'.format(proj_name)), 'w') as out_f:
		out_f.write(out_string)

# ids_file = r'C:\temp\ids.txt'
# ids2sql(ids_file)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('input_file', type=str, help='File containing one id per line.')
	ars = parser.parse_args()
	ids2sql(args.input_file)
