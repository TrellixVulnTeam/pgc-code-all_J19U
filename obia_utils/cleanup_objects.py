import argparse
import copy
import os

import geopandas as gpd

from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

# Create mask based on raster NoData

# mask_on = r'E:\disbr007\umn\2020sep27_eureka\dems\sel\WV02_20140703_1030010033A84300_1030010032B54F00_test_aoi' \
#           r'\WV02_20140703_1030010033A84300_1030010032B54F00_2m_lsf_seg1_dem_masked_test_aoi.tif'
# obj_p = r'E:\disbr007\umn\2020sep27_eureka\seg\grm\ms' \
#         r'\WV02_20140703013631_1030010032B54F00_14JUL03013631' \
#         r'-M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi_bst200x0ni250s0spec0x5spat0x6.shp'
#
# mask_out_img = r'E:\disbr007\umn\2020sep27_eureka\scratch\mask.tif'
# # mask_out_vec = r'E:\disbr007\umn\2020sep27_eureka\scratch\mask.shp'
# mask_out_vec = r'/vsimem/mask_vec.shp'
#
# r = Raster(mask_on)
# r.WriteMaskVector(mask_out_vec)
#
# mask = gpd.read_file(mask_out_vec)
# good = mask[mask['label']!='1']
#
# objs = gpd.read_file(obj_p)
#
# keep_objs = gpd.overlay(objs, good)

def mask_objs(objects, mask_on, out_objects, out_mask_img=None, out_mask_vec=None):
    if out_mask_img is None:
        out_mask_img = r'/vsimem/temp_mask.tif'
    if out_mask_vec is None:
        out_mask_vec = r'/vsimem/temp_mask.shp'

    # Write mask vector (and raster if desired)
    logger.info('Creating mask from raster: {}'.format(mask_on))
    Raster(mask_on).WriteMaskVector(out_vec=out_mask_vec, out_mask_img=out_mask_img)
    mask = gpd.read_file(out_mask_vec)
    not_mask = mask[mask.iloc[:, 0] != '1']
    # Load objects
    # TODO: Read in chunks, parallelize, recombine and write
    logger.info('Reading in objects...')
    objs = gpd.read_file(objects)
    logger.info('Objects found: {:,}'.format(len(objs)))

    # Select only objects in valid areas of mask
    logger.info('Removing objects in masked areas...')
    # TODO: use centroids for faster cleanup - Begin
    objs_centroids = copy.deepcopy(objs).set_geometry(objs.geometry.centroid)
    # use centroids for faster cleanup - End

    keep_objs = gpd.overlay(objs, not_mask)
    logger.info('Objects kept: {:,}'.format(len(keep_objs)))

    logger.info('Writing kept objects to: {}'.format(out_objects))
    keep_objs.to_file(out_objects)
    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remove objects that fall within NoData'
                                                 'areas of passed raster.')
    parser.add_argument('-r', '--raster', type=os.path.abspath,
                        help='Path to raster to use to remove objects in NoData areas.')
    parser.add_argument('-i', '--input_objects', type=os.path.abspath,
                        help='Path to objects to clean up.')
    parser.add_argument('-o', '--out_objects', type=os.path.abspath,
                        help='Path to write cleaned objects to.')
    parser.add_argument('--out_mask_img', type=os.path.abspath,
                        help='Path to write intermediate mask raster derived '
                             'from raster.')
    parser.add_argument('--out_mask_vec', type=os.path.abspath,
                        help='Path to write intermediate mask vector polygonized '
                             'from mask raster.')

    args = parser.parse_args()

    import sys
    sys.argv['-i',
             'seg\grm\ms\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-' \
             '500287602150_01_P009_u16mr3413_pansh_test_aoi_bst150x0ni200s0spec0x3spat0x9.shp',
             '-o', 'seg\grm\ms\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-' \
                   '500287602150_01_P009_u16mr3413_pansh_test_aoi_bst150x0ni200s0spec0x3spat0x9.shp',
             ' -r',
             'dems\sel\WV02_20110811_103001000D198300_103001000C5D4600_test_aoi' \
             '\WV02_20110811_103001000D198300_103001000C5D4600_2m_lsf_seg1_dem_masked_test_aoi.tif']

    raster = args.raster
    input_objects = args.input_objects
    out_objects = args.out_objects
    out_mask_img = args.out_mask_img
    out_mask_vec = args.out_mask_vec

    mask_objs(objects=input_objects, mask_on=raster, out_objects=out_objects,
              out_mask_img=out_mask_img, out_mask_vec=out_mask_vec)
