import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# from selection_utils.query_danco import query_footprint, generate_sql
from selection_utils.db_utils import Postgres, generate_sql
from misc_utils.logging_utils import create_logger
from misc_utils.utm_area_calc import area_calc

logger = create_logger(__name__, 'sh', 'DEBUG')

plt.style.use('pycharm')

logger.debug('Loading coastline...')
coast_p = r'E:\disbr007\general\coastline\countries_dissolve_lines.shp'
coast = gpd.read_file(coast_p)

db = 'danco.footprint'
index_dg = 'index_dg'

years = [year for year in range(2007, 2021, 1)]
base_where = """(platform IN ('WV02', 'WV03') AND cloudcover <= 20)"""

scenes_coast = gpd.GeoDataFrame()
with Postgres(db) as pg:
    for year in years:
        scenes_yr_cst = gpd.GeoDataFrame()
        logger.info('Loading records for {}...'.format(year))
        year_where = "{} AND (acqdate >= '{}-01-01') AND (acqdate <= '{}-12-31')".format(base_where, year, year)
        ct_sql = generate_sql(layer=index_dg, where=year_where, columns=['*'],)

        yr_ct = pg.get_sql_count(sql=ct_sql)
        logger.info('Total count for year {}: {:,}'.format(year, yr_ct))
        chunk_size = 5_000
        for i in range(0, yr_ct, chunk_size):
            logger.debug('Loading records: {:,} - {:,}'.format(i, i+chunk_size))
            sql = generate_sql(layer=index_dg, where=year_where, columns=['*'],
                               geom_col='shape', encode_geom_col='geom',
                               limit=chunk_size, offset=i)
    
            scenes_year = pg.sql2gdf(sql=sql, geom_col='geom')
            logger.debug('Records loaded: {:,}'.format(len(scenes_year)))

            # Intersect with coastline
            if len(scenes_year) == 0:
                continue

            logger.debug('Locating scenes along coast...')
            scenes_yr_cst_chunk = gpd.sjoin(scenes_year, coast)
            logger.debug('Coastal scenes for {} chunk {:,} - {:,}: {}'.format(year, i, i+chunk_size,
                                                                              len(scenes_yr_cst_chunk)))
            scenes_yr_cst = pd.concat([scenes_yr_cst, scenes_yr_cst_chunk])

        scenes_coast = pd.concat([scenes_coast, scenes_yr_cst])
        logger.info('Scenes along coast ({}): {:,}'.format(year, len(scenes_yr_cst)))

logger.info('Done.')

# scenes_coast = gpd.read_file(r'E:\disbr007\projects\coastline\global_coast_scenes_WV02_WV03_2020jul13.shp')
scenes_coast = scenes_coast.drop_duplicates(subset='catalogid')
scenes_coast_area = area_calc(scenes_coast)

cid_sql = generate_sql(layer='pgc_imagery_catalogids', columns=['catalog_id'], where="catalog_id LIKE ('103%') OR catalog_id LIKE ('104%')")
with Postgres(db) as pg:
    # lyrs = pg.list_db_tables()
    cids_oh = pg.execute_sql(sql=cid_sql)
    cids_oh = set([x[0] for x in cids_oh])

scenes_coast_area['onhand'] = scenes_coast_area['catalogid'].isin(cids_oh)

total_coastal_scenes = len(scenes_coast_area)
total_coastal_area = scenes_coast_area['area_sqkm'].sum()

agg = {'sqkm': 'sum',
       'catalogid': 'nunique',}
scenes_coast_agg = scenes_coast_area.groupby([scenes_coast_area['acqdate'].str[:4], 'onhand']).agg(agg)
scenes_coast_agg['sqkm(M)'] = scenes_coast_agg['sqkm'] / 10e5

ren = {'catalogid': 'count',
       'acqdate': 'year'}

scenes_coast_agg.reset_index(inplace=True)
scenes_coast_agg.rename(columns=ren, inplace=True)



