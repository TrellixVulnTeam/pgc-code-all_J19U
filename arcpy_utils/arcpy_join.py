import argparse
import os

import arcpy

from arcpy_utils.arcpy_utils import get_count, get_unique_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

arcpy.env.qualifiedFieldNames

# layer = r'V:\pgc\data\common\quickbase\1744\jones_farq_init_selection.shp'
# # join_table = r'V:\pgc\data\common\quickbase\1744\Request_Spreadsheet\Jones_Farquharson_Images_forPGC.xls'
# join_table = r'V:\pgc\data\common\quickbase\1744\Request_Spreadsheet\Copy of Jones_Farquharson_Images_forPGC.csv'
# layer_field = 'catalog_id'
#
# join_field = 'Image ID'
# by_field = 'Region'
# join_type='KEEP_COMMON'


def table_join(layer, layer_field, join_table, join_field, join_type=None):
    arcpy.env.qualifiedFieldNames = False

    in_mem_tbl = r"in_memory\table"
    tbl = arcpy.MakeTableView_management(join_table, in_mem_tbl)

    logger.debug('Records in source layer of join: {}'.format(get_count(layer)))
    logger.debug('Records in join table: {}'.format(get_count(tbl)))

    joined = arcpy.AddJoin_management(in_layer_or_view=layer,
                                      in_field=layer_field,
                                      join_table=join_table,
                                      join_field=join_field,
                                      join_type=join_type)

    arcpy.Delete_management(tbl)

    joined = arcpy.CopyFeatures_management(in_features=joined, out_feature_class=r"in_memory\temp",)

    return joined



if __name__ == '__main__':
    arcpy.env.overwriteOutput = True

    parser = argparse.ArgumentParser()

    parser.add_argument('-l', '--layer', type=os.path.abspath,
                        help='Source layer to add join to.')
    parser.add_argument('-lf', '--layer_field', type=str,
                        help='Field in source layer to join on.')
    parser.add_argument('-j', '--join_table', type=os.path.abspath,
                        help='Table to join to source.')
    parser.add_argument('-jf', '--join_field', type=str,
                        help='Field in join_table to join on.')
    parser.add_argument('-o', '--out_layer', type=os.path.abspath,
                        help='Path to write layer with join to.')
    parser.add_argument('--keep_all', action='store_true',
                        help='Keep all records in layer, regardless of if a match was found.')

    args = parser.parse_args()

    layer = args.layer
    join_table = args.join_table
    layer_field = args.layer_field
    join_field = args.join_field
    out_layer = args.out_layer
    if args.keep_all:
        join_type = 'KEEP_ALL'
    else:
        join_type = 'KEEP_COMMON'

    joined = table_join(layer=layer, layer_field=layer_field,
                        join_table=join_table, join_field=join_field,
                        join_type=join_type)


    logger.info('Saving layer to: {}'.format(out_layer))
    arcpy.CopyFeatures_management(joined, out_layer)

    begin_count = get_count(layer)
    end_count = get_count(joined)
    logger.debug('Records in source layer with join: {}'.format(end_count))

    if begin_count != end_count:
        logger.debug('Match not found for all values in layer join field...')
        layer_join_values = set(get_unique_ids(layer, field=layer_field))
        joined_values = set(get_unique_ids(out_layer, field=layer_field))
        logger.debug('Missing values:\n{}'.format('\n'.join(layer_join_values-joined_values)))