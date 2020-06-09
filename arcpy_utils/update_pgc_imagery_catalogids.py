import logging
import os

import arcpy

# args
dryrun = True
verbose = False

def get_platform_code(platform):
    platform_code = {
                'QB02': '101',
                'WV01': '102',
                'WV02': '103',
                'WV03': '104',
                'WV03-SWIR': '104A',
                'GE01': '105',
                'IK01': '106'
                }

    return platform_code[platform]


def get_unique_ids(table, field, where=None, clean_fxn=None):
    """
    Loads unique IDs from the given field in the given table, optionally
    with the provided where clause

    Parameters:
    table: os.path.abspath
        The path to the table to parse.
    field: str
        The field in table to parse.
    where: str
        SQL where clause to subset table.

    Returns:
    set: unique values from the given field
    """
    logger.debug('Loading {} IDs WHERE {}'.format(os.path.basename(table), where))

    unique_ids = set()
    for row in arcpy.da.SearchCursor(in_table=table, field_names=[field], where_clause=where):
        the_id = row[0]
        if clean_fxn:
            the_id = clean_fxn(the_id)
        unique_ids.add(the_id)

    logger.debug('Unique IDs: {:,}'.format(len(unique_ids)))

    return unique_ids


def compare_tables(tbl_a, tbl_b,
                   field_a, field_b,
                   where_a=None, where_b=None,
                   clean_fxn_a=None, clean_fxn_b=None):
    """
    Compares the values in two tables, return two sets, the values in
    table A not in table B, and the values in table B not in table A.

    Parameters:
    tbl_a: os.path.abspath
        The path to the first table to parse.
    tbl_b: os.path.abspath
        The path to the second table to parse.
    field_a: str
        The field in table A to parse.
    tbl_b: str
        The field in table B to parse.
    where_a: str
        SQL where clause to subset table A.
    where_b: str
        SQL where clause to subset table B.
    clean_fxn_a: function
        The function to apply to each value in table A before comparing.
    clean_fxn_b: function
        The function to apply to each value in table B before comparing.

    Returns:
    tuple: with two sets (missing from table A, missing from table B)
    """
    tbl_a_vals = get_unique_ids(table=tbl_a, field=field_a, where=where_a, clean_fxn=clean_fxn_a)
    tbl_b_vals = get_unique_ids(table=tbl_b, field=field_b, where=where_b, clean_fxn=clean_fxn_b)
    missing_from_a = tbl_b_vals - tbl_a_vals
    missing_from_b = tbl_a_vals - tbl_b_vals

    return (missing_from_a, missing_from_b)


def cid_from_sid(sid):
    """Parses a catalog_id from a scene_id"""
    try:
        cid = sid.split('_')[2]
    except IndexError:
        cid = None

    return cid


def update_table(sde, table, catid_fld, sensor_fld, new_ids, missing_catids, dryrun=False):
    """Updates the given table by adding the ids in new ids and removes the
    ids in missing ids (if any passed).

    Parameters:
    sde: os.path.abspath
        Path to the sde file of the database containing table.
    table: os.path.abspath
        Path to the table to update
    catid_fld: str
        Name of the catalog_id field to update.
    sensor_fld: str
        Name of the sensor field to update.
    new_ids: dict
        sensor: set of ids to add to table
    missing_catids: set
        ids to remove from table

    Returns:
    None
    """
    # Start editing
    edit = arcpy.da.Editor(sde)
    edit.startEditing(False, True)
    edit.startOperation()
    logger.info('Appending new catalog IDs to: {}'.format(table))
    with arcpy.da.InsertCursor(table, [catid_fld, sensor_fld]) as icur:
        i = 0
        for platform, cids in new_ids.items():
            for cid in cids:
                logger.debug('Appending {}: {} - {}'.format(i, cid, platform))
                if not dryrun:
                    icur.InsertRow([cid, platform])
                i += 1
    del icur
    edit.stopOperation()
    logger.info('Records added to {}: {:,}'.format(table, i))

    if missing_catids:
        # Delete missing
        edit.startOperation()
        logger.info('Deleting missing catalog IDs from: {}'.format(table))
        with arcpy.da.UpdateCursor(table, [catid_fld]) as ucur:
            i = 0
            for row in ucur:
                catid = row[0]
                if catid in missing_catids:
                    logger.debug('Deleting {}'.format(catid))
                    if not dryrun:
                        ucur.deleteRow()
                    i += 1
        del ucur
        edit.stopOperation()
        logger.info('Records deleted from {}: {}'.format(table, i))

    edit.stopEditing(True)

    logger.debug('Getting updated count for {}'.format(table))
    table_catid_count = int(arcpy.GetCount_management(table).getOutput(0))
    logger.info('{} updated count: {:,}'.format(table, table_catid_count))


#### Logging setup
logger = logging.getLogger(__name__)
if verbose:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logger.setLevel(logging_level)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

#### Paths to sde files and tables
dgarchive_sde = r'C:\dbconn\sandwich-pool.dgarchive.sde'
canon_catid_table = 'dgarchive.footprint.canon_catalog_ids'
canon_catid_table_abs = os.path.join(dgarchive_sde, canon_catid_table)
canon_sid_tbl = 'dgarchive.footprint.canon_scene_ids'
canon_sid_tbl_abs = os.path.join(dgarchive_sde, canon_sid_tbl)

danco_sde = r'C:\dbconn\footprint.sde'
danco_catid_table = 'footprint.sde.pgc_imagery_catalogids'
danco_catid_table_abs = os.path.join(danco_sde, danco_catid_table)
danco_stereo_tbl = 'footprint.sde.pgc_imagery_catalogids_stereo'
danco_stereo_tbl_abs = os.path.join(danco_sde, danco_stereo_tbl)

#### Constants
platforms = ['QB02', 'WV01', 'WV02', 'WV03', 'GE01', 'IK01']
catid_fld = 'catalog_id'
sid_fld = 'scene_id'
sensor_fld = 'sensor'
other = 'other'  # used as key for IDs that don't conform to the platform code


#### Starting table counts
starting_counts = dict()
for tbl in [danco_catid_table_abs, danco_stereo_tbl_abs]:
    tbl_count = int(arcpy.GetCount_management(tbl).getOutput(0))
    logger.debug('{} starting count: {:,}'.format(os.path.basename(tbl), tbl_count))
    starting_counts[tbl] = tbl_count


#### Update danco table: pgc_imagery_catalogids
logger.info('Determining required updates for {}...'.format(danco_catid_table))
new_catids = dict()
missing_catids = set()
# Load each platform's IDs for canon_catalog_ids and pgc_imagery_catalogids, find difference
for platform in platforms:
    logger.info('Parsing {} IDs...'.format(platform))
    # Create where clause to select only IDs that start with platform code
    where = """{} LIKE '{}%'""".format(catid_fld, get_platform_code(platform))
    # Identify new and missing IDs for platform
    new_platform, missing_platform = compare_tables(tbl_a=danco_catid_table_abs,
                                                    tbl_b=canon_catid_table_abs,
                                                    field_a=catid_fld, field_b=catid_fld,
                                                    where_a=where, where_b=where)
    logger.info('New IDs for {}: {:,}'.format(platform, len(new_platform)))
    logger.info('Missing IDs for {}: {:,}'.format(platform, len(missing_platform)))
    # Capture new and missing IDs
    new_catids[platform] = new_platform
    missing_catids = missing_catids | missing_platform

    del new_platform, missing_platform

# Catch all for any old/other format IDs (that don't start with platform codes)
logger.info('Parsing all other IDs....')
where = str()
for platform in platforms:
    if where:
        where += ' AND '
    where += "({} NOT LIKE '{}%')".format(catid_fld, get_platform_code(platform))

new_other, missing_other = compare_tables(tbl_a=danco_catid_table_abs,
                                          tbl_b=canon_catid_table_abs,
                                          field_a=catid_fld, field_b=catid_fld,
                                          where_a=where, where_b=where)

logger.info('New IDs with unrecognized platform code: {}'.format(len(new_other)))
logger.info('Missing IDs with unrecognized platform code: {}'.format(len(missing_other)))
new_catids[other] = new_other
missing_catids = missing_catids | missing_other

del new_other, missing_other
logger.info('\n')

# Perform updates: pgc_catalogids
logger.info('Making updates to {}'.format(danco_catid_table))
# if not dryrun:
update_table(danco_sde, danco_catid_table_abs,
             catid_fld=catid_fld, sensor_fld=sensor_fld,
             new_ids=new_catids, missing_catids=missing_catids,
             dryrun=dryrun)

    # # Start editing
    # edit = arcpy.da.Editor(danco_sde)
    # edit.startEditing(False, True)
    # edit.startOperation()
    # logger.info('Appending new catalog IDs to: {}'.format(danco_catid_table))
    # with arcpy.da.InsertCursor(danco_catid_tbl_abs, [catid_fld, sensor_fld]) as icur:
    #     i = 0
    #     for platform, cids in new_catids.items():
    #         for cid in cids:
    #             logger.debug('Appending {}: {} - {}'.format(i, cid, platform))
    #             if not dryrun:
    #                 icur.InsertRow([cid, platform])
    #                 i += 1
    # del icur
    # edit.stopOperation()
    # logger.info('Records added to {}: {}'.format(danco_catid_table, i))
    #
    # # Delete missing
    # edit.startOperation()
    # logger.info('Deleting missing catalog IDs from: {}'.format(danco_catid_table))
    # with arcpy.da.UpdateCursor(danco_catid_table_abs, [catid_fld]) as ucur:
    #     i = 0
    #     for row in ucur:
    #         cid = row[0]
    #         if catid in missing_catids:
    #             logger.debug('Deleting {}'.format(catid))
    #             if not dryrun:
    #                 ucur.deleteRow()
    #             i += 1
    # del ucur
    # edit.stopOperation()
    # logger.info('Records deleted from {}: {}'.format(danco_catid_table, i))
    # logger.debug('Getting updated count for {}'.format(danco_catid_table))
    # danco_catid_count = int(arcpy.GetCount_management(danco_catid_table_abs).getOutput(0))
    # logger.info('{} updated count: {}'.format(danco_catid_table, danco_catid_count))

del new_catids, missing_catids

logger.info('\n\n')


#### Update danco table: pgc_imagery_ids_stereo
logger.info('Determining required updates for {}'.format(danco_stereo_tbl))
new_stereo_catids = dict()
missing_stereo_catids = set()
for platform in platforms:
    logger.info('Parsing {} IDs...'.format(platform))
    # Where clauses
    danco_where = """{} LIKE '{}%'""".format(catid_fld, get_platform_code(platform))
    canon_where = """{0} LIKE '{1}%' AND {0} LIKE '%P1BS%'""".format(sid_fld, platform)
    # Identify new and missing IDs for platform
    new_platform, missing_platform = compare_tables(tbl_a=danco_stereo_tbl_abs,
                                                    tbl_b=canon_sid_tbl_abs,
                                                    field_a=catid_fld,
                                                    field_b=sid_fld,
                                                    where_a=danco_where,
                                                    where_b=canon_where,
                                                    clean_fxn_a=None,
                                                    clean_fxn_b=cid_from_sid)
    logger.info('New IDs for {}: {:,}'.format(platform, len(new_platform)))
    logger.info('Missing IDs for {}: {:,}'.format(platform, len(missing_platform)))
    # Capture new and missing IDs
    new_stereo_catids[platform] = new_platform
    missing_stereo_catids = missing_stereo_catids | missing_platform

    del new_platform, missing_platform

# Catch all for any old/other format IDs (that don't start with platform codes)
logger.info('Parsing all other IDs....')
danco_where = str()
canon_where = str()
for platform in platforms:
    if danco_where:
        danco_where += ' AND '
    danco_where += "({} NOT LIKE '{}%')".format(catid_fld, get_platform_code(platform))
    if canon_where:
        canon_where += ' AND '
    canon_where += "({} NOT LIKE '{}%')".format(sid_fld, platform)

new_other, missing_other = compare_tables(tbl_a=danco_stereo_tbl_abs,
                                          tbl_b=canon_sid_tbl_abs,
                                          field_a=catid_fld, field_b=sid_fld,
                                          where_a=danco_where, where_b=canon_where,
                                          clean_fxn_a=None, clean_fxn_b=cid_from_sid)

logger.info('New IDs with unrecognized platform code: {:,}'.format(len(new_other)))
logger.info('Missing IDs with unrecognized platform code: {:,}'.format(len(missing_other)))
new_stereo_catids[other] = new_other
missing_stereo_catids = missing_stereo_catids | missing_other

del new_other, missing_other
logger.info('\n')

# Perform updatea: pgc_imagery_catalogids_stereo
# if not dryrun:
update_table(danco_sde, danco_stereo_tbl_abs,
             catid_fld=catid_fld, sensor_fld=sensor_fld,
             new_ids=new_stereo_catids, missing_catids=missing_stereo_catids,
             dryrun=dryrun)


# Compare starting counts and ending counts
for tbl in [danco_catid_table_abs, danco_stereo_tbl_abs]:
    logger.debug('{} starting count: {:,}'.format(os.path.basename(tbl), starting_counts[tbl]))
    tbl_count = int(arcpy.GetCount_management(tbl).getOutput(0))
    logger.debug('{} ending count:   {:,}'.format(os.path.basename(tbl), tbl_count))
