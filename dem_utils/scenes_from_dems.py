import copy
import re
from datetime import datetime

import pandas as pd
import geopandas as gpd

from selection_utils.db import Postgres
from selection_utils.danco_utils import get_stereo_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


def sceneids_regex_from_demid(scenedemid, no_order_id=False):
    scene_pattern = re.compile("""(?P<groupid>
                                  (?P<pairname>
                                  (?P<sensor>[A-Z][A-Z\d]{2}\d)_
                                  (?P<timestamp>\d{8})_
                                  (?P<catid1>[A-Z0-9]{16})_
                                  (?P<catid2>[A-Z0-9]{16})
                                  )_
                                  (?P<tile1>R\d+C\d+)?-?
                                  (?P<order1>\d{12}_\d{2}_
                                  (?P<part1>P\d{3}))_
                                  (?P<tile2>R\d+C\d+)?-?
                                  (?P<order2>\d{12}_\d{2}_
                                  (?P<part2>P\d{3}))_
                                  (?P<res>[0128])
                                  )_?
                                  (?P<component>[\w_]+)?""", re.I | re.X)

    reg_match = scene_pattern.match(scenedemid)
    gd = reg_match.groupdict()
    if not no_order_id:
        scene_re = re.compile(f"{gd['sensor']}_{gd['timestamp']}\d{{6}}_"
                              f"({gd['catid1']}|{gd['catid2']})_"
                              f"\d{{2}}[A-Z]{{3}}\d{{8}}-"
                              f"[A-Z0-9]{{4}}-([A-Z]*-)?"
                              f"({gd['order1']}|{gd['order2']})", re.VERBOSE)
    else:
        scene_re = re.compile(f"{gd['sensor']}_{gd['timestamp']}\d{{6}}_"
                              f"({gd['catid1']}|{gd['catid2']})_"
                              f"\d{{2}}[A-Z]{{3}}\d{{8}}-"
                              f"[A-Z0-9]{{4}}-([A-Z]*-)?"
                              f"(.*)_"
                              f"({gd['part1']}|{gd['part2']})"
                              f"(.*)", re.VERBOSE)

    return scene_re


def sceneids_from_demid(scenedemid, scene_ids, wide_search=True):
    scene_re = sceneids_regex_from_demid(scenedemid)
    matching_scenes = scene_ids[scene_ids.str.contains(scene_re, regex=True)]

    if len(matching_scenes) == 0 and wide_search:
        scene_re = sceneids_regex_from_demid(scenedemid, no_order_id=True)
        matching_scenes = scene_ids[scene_ids.str.contains(scene_re, regex=True)]

    return matching_scenes.values


def get_sceneids_from_dems(dems, scene_ids, wide_search=True):
    dems['scenes'] = dems['scenedemid'].apply(lambda x: sceneids_from_demid(x, scene_ids, wide_search=wide_search))
    sids = set(dems['scenes'].explode())

    return sids

# dems = gpd.read_file(r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\shp\kamchatka_points_dems.shp')
# scenes = gpd.read_file(r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\kamchatka_points_dems_aoi_scenes.shp')
# scenes = scenes[scenes['prod_code']=='P1BS']
# scene_ids = scenes['scene_id']

# scenedemid = 'WV02_20190420_1030010090B7FF00_10300100900F4D00_503186697080_01_P001_503186858070_01_P001_0'