import argparse
import os

import geopandas as gpd

from misc_utils.logging_utils import create_logger


fp_p = r'V:\pgc\data\scratch\jeff\deliverables\kmelocik_senegal\senegal_stereo_cc20_nohNASA_catalogid.shp'
cid_field = 'catalogid'
stp_field = 'stereopair'


logger = create_logger(__name__, 'sh', 'INFO')

def stack_stereo_ids(footprint, cid_field='catalogid', stp_field='stereopair'):
    logger.info('Reading source footprint: {}'.format(footprint))
    fp = gpd.read_file(fp_p)
    logger.info('Stereo records found: {}'.format(len(fp)))

    cids = set(fp[cid_field])
    logger.info('Unique catalogids found: {}'.format(len(cids)))
    stps = set(fp[stp_field])
    logger.info('Unique stereopairs found: {}'.format(len(cids)))
    both = cids.union(stps)
    logger.info('Total unique IDs found: {}'.format(len(both)))

    return both


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--stereo_footprint', type=os.path.abspath,
                        help='Path to stereo footprint.')
    parser.add_argument('-o', '--out_ids', type=os.path.abspath,
                        help='Path to write IDs to.')
    parser.add_argument('-cid', '--catalogid_field', type=str, default='catalogid',
                        help='Field catalogids are stored in.')
    parser.add_argument('-stp', '--stereopair_field', type=str, default='stereopair',
                        help='Field stereopairs are stored in.')

    args = parser.parse_args()

    stacked_ids = stack_stereo_ids(args.stereo_footprint, cid_field=args.cid, stp_field=args.stp)

    logger.info('Writing IDs to: {}'.format(args.out_ids))
    with open(args.out_ids, 'w') as src:
        for i in stacked_ids:
            src.write(i)
            src.write('\n')
