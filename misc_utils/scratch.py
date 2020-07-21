import copy
import re

import geopandas as gpd

from selection_utils.db_utils import Postgres
from selection_utils.danco_utils import get_stereo_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

sql = """SELECT * FROM dem.scene_dem_master WHERE scenedemid LIKE 'WV01_20190828_102001008B657000_%'"""

scenes_p = r'V:\pgc\data\scratch\jeff\deliverables\4256_kschild_imagery\init_scenes.shp'
#TODO: better way to select a single DEM if multiple results, just selecting biggest filesz
single_dem = True

dem_tbl = 'dem.scene_dem_master'
sid_col = 'scene_id'
cid_col = 'catalog_id'
dem_cid1_col = 'catalogid1'
dem_cid2_col = 'catalogid2'
dem_geom_col = 'wkb_geometry'
scenedemid_col = 'scenedemid'
filesz_col = 'filesz_dem'
dem_res = 2.0


scene_pattern = re.compile("""(?P<groupid>
                              (?P<pairname>
                              (?P<sensor>[A-Z][A-Z\d]{2}\d)_
                              (?P<timestamp>\d{8})_
                              (?P<catid1>[A-Z0-9]{16})_
                              (?P<catid2>[A-Z0-9]{16})
                              )_
                              (?P<tile1>R\d+C\d+)?-?
                              (?P<order1>\d{12}_\d{2}_P\d{3})_
                              (?P<tile2>R\d+C\d+)?-?
                              (?P<order2>\d{12}_\d{2}_P\d{3})_
                              (?P<res>[0128])
                              )_?
                              (?P<component>[\w_]+)?""", re.I | re.X)


def find_scene_dem(sid, dem_res, dems):
    cid = sid[20:36]
    oid = sid[-20:]
    # reg = '{}_{}.*_{}_{}'.format(sid[:13], sid[20:36], sid[-20:], round(dem_res))
    reg = '.*_{}.*_{}.*_{}'.format(cid, oid, round(dem_res))
    matches = dems[dems[scenedemid_col].str.contains(reg, regex=True, na=False)]

    if len(matches) > 0:
        # Take largest filesize
        dem_id = matches.loc[matches[filesz_col].idxmax()][scenedemid_col]
    else:
        dem_id = None

    return dem_id


def find_scenes_from_demid(scenedemid, scenes):
    s = copy.deepcopy(scenes)
    s = s[s['prod_code']=='P1BS']

    reg_match = scene_pattern.match(scenedemid)
    if not reg_match:
        print('No match: {}'.format(scenedemid))

    gd = reg_match.groupdict()

    scene_matches = s[((s['catalog_id'] == gd['catid1']) | (s['catalog_id'] == gd['catid2'])) &
                      ((s['order_id'] == gd['order1']) | (s['order_id'] == gd['order2']))]
    if len(scene_matches) > 2:
        print('more than two match:\n{}'.format(scenedemid))
        print(scene_matches['scene_id'].values)
        print(scene_matches['order_id'].values)
        for k, v in gd.items():
            print('{}: {}'.format(k, v))

        print('\n\n')
    return list(scene_matches['scene_id'])


def lookup_scenedemid(sid, dems, dem_scene_col):
    # matches = dems[dems[dem_scene_col].contains(sid)]
    # print(len(matches))
    matches = []
    for i, row in dems.iterrows():
        if sid in row[dem_scene_col]:
            matches.append(row[scenedemid_col])
    if len(matches)==0:
        matches = None

    return matches


scenes = gpd.read_file(scenes_p)
scenes = scenes[scenes['prod_code']=='P1BS']
scene_cids = set(scenes[cid_col])

with Postgres('sandwich-pool.dem') as db_src:
    # all_cid_dems_sql = """SELECT * FROM {0} WHERE {1} IN ({2}) OR {3} IN ({2})""".format(dem_tbl, dem_cid1_col,
    #                                                                            str(scene_cids)[1:-1],
    #                                                                            dem_cid2_col)
    logger.debug('Loading DEMs...')
    all_cid_dems_sql = """SELECT * FROM {0} WHERE acqdate1 > '2019-06-20' AND acqdate2 < '2020-01-01'""".format(dem_tbl)
    all_cid_dems = db_src.sql2gdf(sql=all_cid_dems_sql, geom_col=dem_geom_col)

logger.debug('Matching DEMs and scenes')
# all_cid_dems['scene_ids'] = all_cid_dems.apply(lambda x: find_scenes_from_demid(x[scenedemid_col], scenes), axis=1)
# scenes[scenedemid_col] = scenes.apply(lambda x: lookup_scenedemid(x[sid_col], all_cid_dems, 'scene_ids'), axis=1)

scenes[scenedemid_col] = scenes.apply(lambda x: find_scene_dem(x[sid_col], dem_res=dem_res, dems=all_cid_dems), axis=1)
# dem_match_ids = set(list(scenes[~scenes[scenedemid_col].isnull()][scenedemid_col]))
# dem_matches = all_cid_dems[all_cid_dems[scenedemid_col].isin(dem_match_ids)]
#
# no_matches = scenes[scenes[scenedemid_col].isnull()]
# print(len(dem_matches))
# print(len(no_matches))
#
# stereo_where = "{0} IN ({1}) OR {2} IN ({1})".format('catalogid', str(scene_cids)[1:-1], 'stereopair')
# stereo_ids = get_stereo_ids(where=stereo_where)
#
# scenes['is_stereo'] = scenes[cid_col].isin(stereo_ids)
#
# scenes['stereo_nodem'] = ((scenes['prod_code']=='P1BS') &
#                       (scenes['is_stereo'] == True) &
#                       (scenes[scenedemid_col].isnull()))

# stereo_nodem = scenes[(scenes['prod_code']=='P1BS') &
#                       (scenes['is_stereo'] == True) &
#                       (scenes[scenedemid_col].isnull())]
# stereo_nodem['cid_dem'] = stereo_nodem.apply(lambda x: x[cid_col] in all_cid_dems[dem_cid1_col] or
#                                                        x[cid_col] in all_cid_dems[dem_cid2_col], axis=1)
#
# print(len(stereo_nodem))

# missing_dems = all_cid_dems[(all_cid_dems[dem_cid1_col].isin(stereo_nodem[cid_col])) or
#                             (all_cid_dems[dem_cid2_col].isin(stereo_nodem[cid_col]))]