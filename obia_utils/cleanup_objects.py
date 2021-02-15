import argparse
import copy
import os
from pathlib import PurePath

from osgeo import gdal
import pandas as pd
import geopandas as gpd

from misc_utils.gpd_utils import write_gdf
from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

gdal.UseExceptions()
gdal.SetConfigOption('CHECK_DISK_FREE_SPACE', 'FALSE')


def load_objs(objects):
    if isinstance(objects, PurePath):
        objects = str(objects)
    # Load objects
    # TODO: Read in chunks, parallelize, recombine and write
    logger.info('Reading in objects...')
    objs = gpd.read_file(objects)
    logger.info('Objects found: {:,}'.format(len(objs)))

    return objs


def remove_small_objects(objects, min_size):
    logger.info('Removing objects with area less than {}'.format(min_size))
    objects = objects[objects.geometry.area >= min_size]
    logger.info('Objects kept: {:,}'.format(len(objects)))

    return objects


def mask_objs(objs, mask_on, out_mask_img=None, out_mask_vec=None):
    if out_mask_img is None:
        out_mask_img = r'/vsimem/temp_mask.tif'
    if out_mask_vec is None:
        out_mask_vec = r'/vsimem/temp_mask.shp'

    # Write mask vector (and raster if desired)
    logger.info('Creating mask from raster: {}'.format(mask_on))
    Raster(mask_on).WriteMaskVector(out_vec=out_mask_vec, out_mask_img=out_mask_img)
    mask = gpd.read_file(out_mask_vec)
    not_mask = mask[mask.iloc[:, 0] != '1']

    # Select only objects in valid areas of mask
    logger.info('Removing objects in masked areas...')
    # TODO: use centroids for faster cleanup - Begin
    # objs_centroids = copy.deepcopy(objs).set_geometry(objs.geometry.centroid)
    # use centroids for faster cleanup - End

    keep_objs = gpd.overlay(objs, not_mask)
    logger.info('Objects kept: {:,}'.format(len(keep_objs)))

    return keep_objs


def remove_null_objects(objects, fields=['all']):
    logger.info('Removing objects with fields that are null.')
    if len(fields) == 1 and fields[0] == 'all':
        fields = list(objects)
    logger.info('Fields considered: {}'.format(fields))

    keep_objs = objects[objects.apply(lambda x: all([pd.notna(x[f])
                                                     for f in fields]), axis=1)]
    # keep_objs = keep_objs[keep_objs[fields].notnull()]

    logger.info('Objects kept: {:,}'.format(len(keep_objs)))

    return keep_objs


def cleanup_objects(input_objects,
                    out_objects=None,
                    min_size=None,
                    mask_on=None,
                    out_mask_img=None,
                    out_mask_vec=None,
                    drop_na=None,
                    overwrite=False):

    keep_objs = load_objs(input_objects)

    if min_size:
        keep_objs = remove_small_objects(objects=keep_objs,
                                         min_size=min_size)
    if mask_on:
        keep_objs = mask_objs(objs=keep_objs, mask_on=mask_on,
                              out_mask_img=out_mask_img,
                              out_mask_vec=out_mask_vec)
    if drop_na:
        keep_objs = remove_null_objects(keep_objs, fields=drop_na)

    if out_objects:
        logger.info('Writing kept objects ({:,}) to: {}'.format(len(keep_objs),
                                                                out_objects))
        keep_objs.to_file(out_objects)
        write_gdf(keep_objs, out_objects, overwrite=overwrite)

    return out_objects


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Utility for cleaning up '
                                                 'image-objects after '
                                                 'segmentation.')
    parser.add_argument('-i', '--input_objects', type=os.path.abspath,
                        help='Path to objects to clean up.')
    parser.add_argument('-r', '--raster', type=os.path.abspath,
                        help='Path to raster to use to remove objects in NoData'
                             ' areas.')
    parser.add_argument('-dna', '--drop_na', nargs='+',
                        help='Drop objects where the passed fields are NaN. '
                             'Pass "all" to check all fields for NaN.')
    parser.add_argument('-ms', '--min_size', type=float,
                        help='The minimum size object to keep, in units of CRS')
    parser.add_argument('-o', '--out_objects', type=os.path.abspath,
                        help='Path to write cleaned objects to.')
    parser.add_argument('--out_mask_img', type=os.path.abspath,
                        help='Path to write intermediate mask raster derived '
                             'from raster.')
    parser.add_argument('--out_mask_vec', type=os.path.abspath,
                        help='Path to write intermediate mask vector '
                             'polygonized from mask raster.')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite outfile if it exists.')

    import sys
    # sys.argv = [r'C:\code\pgc-code-all\obia_utils\cleanup_objects.py',
    #             '-i',
    #             r'E:\disbr007\umn\2020sep27_eureka\seg\zs'
    #             r'\WV02_20140703013631_1030010032B54F00_14JUL03013631'
    #             r'-M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi_'
    #             r'bst150x0ni200s0spec0x3spat0x9_zs_cclass.shp',
    #             '-o',
    #             r'E:\disbr007\umn\2020sep27_eureka\seg\zs'
    #             r'\WV02_20140703013631_1030010032B54F00_14JUL03013631'
    #             r'-M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi_'
    #             r'bst150x0ni200s0spec0x3spat0x9_zs_cclass_cln.shp',
    #             '-dna', 'all']

    args = parser.parse_args()

    mask_on = args.raster
    drop_na = args.drop_na
    min_size = args.min_size
    input_objects = args.input_objects
    out_objects = args.out_objects
    out_mask_img = args.out_mask_img
    out_mask_vec = args.out_mask_vec
    overwrite = args.overwrite

    cleanup_objects(input_objects=input_objects,
                    out_objects=out_objects,
                    min_size=min_size,
                    mask_on=mask_on,
                    drop_na=drop_na,
                    out_mask_vec=out_mask_vec,
                    out_mask_img=out_mask_img,
                    overwrite=overwrite)
