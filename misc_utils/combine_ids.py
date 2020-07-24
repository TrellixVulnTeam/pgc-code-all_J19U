import argparse
import os

from id_parse_utils import combine_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')
sublogger = create_logger('id_parse_utils', 'sh', 'DEBUG')


def main(args):
    id_lists = args.id_lists
    fields = args.fields
    out_ids = args.out_ids

    combine_ids(id_lists, fields=fields, write_path=out_ids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--id_lists', nargs='+', type=os.path.abspath,
                        help='Paths to files with IDs to combine.')
    parser.add_argument('--fields', nargs='+', help='Ordered list of fields to use to locate IDs in files. "None" if just text file.')
    parser.add_argument('--out_ids', type=os.path.abspath, help='Path to write combined list of IDs .')

    args = parser.parse_args()
    print(args)
    main(args)
