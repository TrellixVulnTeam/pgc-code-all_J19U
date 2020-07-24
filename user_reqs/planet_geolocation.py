import geopandas as gpd

from selection_utils.db_utils import Postgres, generate_sql, intersect_aoi_where
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')

db = 'sandwich-pool.dem'
tbl = 'dem.scene_dem_master'
geom_col = 'wkb_geometry'

aoi_p = r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\kamchatka\kamchatka_points.shp'
out_dems = r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\shp\kamchatka_points_dems.shp'

aoi = gpd.read_file(aoi_p)
aoi_where = intersect_aoi_where(aoi=aoi, geom_col=geom_col)
where = ' dem_res < 1 AND {}'.format(aoi_where)

logger.info('Loading DEMs...')
sql = generate_sql(layer=tbl, where=where, geom_col=geom_col, encode_geom_col='geom')
logger.debug('SQL: {}'.format(sql))
with Postgres(db_name=db) as dem_db:
    # tbls = dem_db.list_db_tables()
    # cols = dem_db.get_layer_columns(layer=tbl)
    dems = dem_db.sql2gdf(sql=sql)

agg = {'scenedemid': 'count'}
dems_agg = dems.groupby('status').agg(agg)
print(dems_agg)

logger.info('Writing DEM footprints to file: {}'.format(out_dems))
dems.to_file(out_dems)