# -*- coding: utf-8 -*-
"""
Created on Fri May 24 10:31:27 2019

@author: disbr007
CLI to convert old ids to new
takes a text file, returns either only converted as new text and/or not converted seperately
"""

import os, argparse
from id_parse_utils import ge_ids2dg_ids, read_ids, write_ids


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ids_path', type=str, help="Path to text file of ids")
#    parser.add_argument('sensor', type=str, help="Sensor type to convert: 'IK01' or 'GE01'")
    parser.add_argument('--out_dir', type=str, help="Directory to write text file, defaults to ids_path directory")
    parser.add_argument('--not_converted', action='store_true', help="Flag to write not converted ids to text file")

    # Parse arguments    
    args = parser.parse_args()
    ids_path = args.ids_path
#    sensor = args.sensor
    if args.out_dir:
        out_path = args.out_dir
    else:
        out_dir = os.path.dirname(ids_path)
    not_converted = args.not_converted
    
    # Create out paths
    out_name = os.path.basename(ids_path).split('.')[0]
    conv_out = os.path.join(out_dir, '{}_converted.txt'.format(out_name))
    not_conv_out = os.path.join(out_dir, '{}_not_conv.txt'.format(out_name))
    
    # Convert and write ids
    ids = read_ids(ids_path)
    conv_ids, not_conv_ids = ge_ids2dg_ids(ids)
    write_ids(conv_ids, conv_out)
    if not_converted:
        write_ids(not_conv_ids, not_conv_out)