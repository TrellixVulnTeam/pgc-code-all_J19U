import os

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from selection_utils.db import Postgres

logger = create_logger(__name__, 'sh', 'INFO')

logger.info('Loading selection...')
selection_p = r'V:\pgc\data\scratch\jeff\deliverables\4279_kmelocik_intel_challenge\NASA_intel_ethiopia_stereo_noh.shp'
selection = gpd.read_file(selection_p)
logger.info('Total scenes found: {}'.format(len(selection)))
logger.info('Total catids found: {}'.format(len(selection['catalog_id'].unique())))

logger.info('Loading stereo IDs')
with Postgres('danco.footprint') as db:
    # stereo_ids = db.get_values('pgc_imagery_catalogids_stereo', columns='catalog_id')
    dg_stereo = db.get_values('dg_imagery_index_stereo', columns='catalogid')

logger.info('Locating stereo IDs in selection...')
# stereo_selection = selection[selection['catalog_id'].isin(stereo_ids)]
dg_stereo_selection = selection[selection['catalog_id'].isin(dg_stereo)]

logger.info('Stereo scenes found: {}'.format(len(dg_stereo_selection)))

import matplotlib.pyplot as plt
plt.style.use('pycharm')

fig, ax = plt.subplots(1,1)
selection[selection['cloudcover']>=0].hist(column='cloudcover', ax=ax)
fig.show()