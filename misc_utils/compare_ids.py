# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 12:52:32 2019

@author: disbr007
"""

from id_parse_utils import compare_ids
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("list_1", type=str, help="Path to text file of first list of ids.")
    parser.add_argument("list_2", type=str, help="Path to text file of first list of ids.")
    parser.add_argument("-w", "--write", action='store_true', help='Write out common and unique lists.')

    args = parser.parse_args()

    ids1, ids2, com = compare_ids(args.list_1, args.list_2, write_path=args.write)


if __name__ == "__main__":
    main()
