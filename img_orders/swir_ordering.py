import geopandas as gpd
import pandas as pd

from selection_utils.query_danco import count_table, query_footprint
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

index_dg = 'index_dg'
base_where = "catalogid LIKE '104A%%'"
pgc_oh = 'pgc_imagery_catalogids'
pgc_swir_where = "catalog_id LIKE '104A%%'"


earth_dem = 'pgc_earthdem_regions'
ed_where = "project = 'ArcticDEM' OR project = 'REMA'"
dissolve_fld = 'dissolve'
limit = 50000


regions = {'arctic': {'sql': "y1 > 45",
                      'crs': 'epsg:3413',
                      'project': 'ArcticDEM'},
           'antarctic': {'sql': "y1 < -45",
                         'crs': 'epsg:3031',
                         'project': 'REMA'}}

master_swir = gpd.GeoDataFrame()

for region, params in regions.items():
    where = base_where
    ed_region = query_footprint(earth_dem,
                                where="project = '{}'".format(params['project']))
    # ed_region = ed_region.dissolve(by='project')
    uu = gpd.GeoDataFrame(geometry=[ed_region.unary_union], crs='epsg:4326')
    # ed_region = ed_region.to_crs(params['crs'])

    offset = 0
    num_processed = 0
    swir_archive_count = count_table(index_dg, where=where)
    logger.debug('Size of table for {} with WHERE {}: {:,}'.format(index_dg, where, swir_archive_count))
    while num_processed <= swir_archive_count:
        logger.info('Loading with OFFSET {:,} LIMIT {:,}'.format(offset, limit))
        # where += " AND {}".format(params['sql'])
        logger.debug('WHERE {}'.format(where))
        swir = query_footprint(index_dg, where=where, limit=limit, offset=offset)
        logger.debug('Loaded SWIR: {:,}'.format(len(swir)))
        # swir = swir.to_crs(params['crs'])
        swir.geometry = swir.geometry.centroid

        polar_swir = gpd.sjoin(swir, uu, op='within')
        offset += limit
        num_processed = offset

        logger.info('Found {} polar SWIR IDs where project is: {}'.format(len(polar_swir),
                                                                    params['project']))
        if len(polar_swir) != 0:
            master_swir = pd.concat([master_swir, polar_swir])

# Remove on hand swir
oh_swir = set(list(query_footprint(pgc_oh, where=pgc_swir_where, table=True)))

# %% Plotting
import matplotlib.pyplot as plt

plt.style.use('pycharm_blank')

fig, ax = plt.subplots(1,1)
# ed_region.plot(ax=ax, color='none', edgecolor='white')
swir.plot(ax=ax, markersize=0.5)
uu.plot(ax=ax, color='none', edgecolor='white')
master_swir.plot(ax=ax, markersize=0.8)
fig.show()
