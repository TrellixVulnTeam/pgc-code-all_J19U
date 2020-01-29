# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27

@author: disbr007
"""

import argparse
import os
import subprocess

from misc_utils.logging_utils import create_logger


# MFP_PATH = r'C:\pgc_index\pgcImageryIndexV6_2020jan14.gdb\pgcImageryIndexV6_2020jan14'
logger = create_logger(os.path.basename(__file__), 'sh')


def main(MFP_PATH):	
	TXT_LOC = r'C:\code\pgc-code-all\config\pgc_index_path.txt'
	GET_IDS_PY  = r'C:\code\pgc-code-all\misc_utils\mfp_ids.py'

	mfp_name = os.path.basename(MFP_PATH)
	IDS_LOC = os.path.join(os.path.dirname(TXT_LOC), '{}_catalog_id.txt'.format(mfp_name))
	TXT_DIR = os.path.dirname(TXT_LOC)

	logger.info('Updating text file of catalog_ids...')
	cmd = 'python {} --mfp_path {} --ids_out_dir {}'.format(GET_IDS_PY, MFP_PATH, TXT_DIR)
	logger.debug('Calling command:\n{}'.format(cmd))
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = proc.communicate()

	logger.info(stdout)
	logger.info(stderr)


	logger.info('Updating locations of master footprint and catalog_ids.txt...')
	with open(TXT_LOC, 'w') as txt:
		txt.write(MFP_PATH)
		txt.write('\n')
		txt.write(IDS_LOC)


if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	parser.add_argument('mfp_path', type=os.path.abspath,
						help='Path to new master footprint.')

	args = parser.parse_args()
	
	MFP_PATH = args.mfp_path

	main(MFP_PATH)
