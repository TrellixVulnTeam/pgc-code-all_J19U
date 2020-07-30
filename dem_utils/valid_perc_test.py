import os
import ntpath

import pandas as pd
import geopandas as gpd
import dask_geopandas
from tqdm import tqdm

from valid_data import valid_percent
# from dem_utils.valid_data import valid_percent
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

def get_bitmask_path(dem_path):
    bm_p = os.path.join(
        os.path.dirname(dem_path),
        os.path.basename(dem_path).replace('dem', 'bitmask')
    )

    return bm_p


def mnt2v(filepath):
    terranova_root = r'/mnt/pgc'
    windows_root = r'V:\pgc'
    if filepath.startswith(terranova_root):
        filepath = filepath.replace(terranova_root, windows_root)
        filepath = filepath.replace(ntpath.sep, os.sep)

    return filepath


fields = {
    'DEMS_GEOM': 'wkb_geometry',  # Sandwich DEMs geometry name
    # Used only for writing catalogids to text file if requested
    'CATALOGID1': 'catalogid1',  # field name in danco DEM footprint for catalogids
    'CATALOGID2': 'catalogid2',
    'PAIRNAME': 'pairname',
    'FULLPATH': 'LOCATION',  # field name in footprint with path to dem file
    'BITMASK': 'bitmask',  # created field name in footprint to hold path to bitmask
    'DATE_COL': 'acqdate1',  # name of date field in dems footprint
    'DENSITY_COL': 'density',  # name of density field in dems footprint
    'SENSOR_COL': 'sensor1',  # name of sensor field in dems footprint
    'RES_COL': 'dem_res',
}

VALID_PERC = 'valid_perc'

dems_p = r'V:\pgc\data\scratch\jeff\projects\nasa_planet_geoloc\kamchatka\kamchatka_points_buff_intrack_strips_2m.shp'
dems = gpd.read_file(dems_p)
# dems = dems[0:50]
# dems = dask_geopandas.from_geopandas(dems, npartitions=4)


dems['winpath'] = dems[fields['FULLPATH']].apply(lambda x: mnt2v(x))
                                                 #meta=(fields['FULLPATH'], 'object'))
dems[fields['BITMASK']] = dems['winpath'].apply(lambda x: get_bitmask_path(x))
                                                #meta=('winpath', 'object'))
# dems = dems[0:10]
dems[VALID_PERC] = -9999.0
logger.info('Determining percent of non-NoData pixels over AOI for each DEM...')
for row in tqdm(dems[[fields['BITMASK']]].itertuples(),
                total=len(dems)):
    vp = valid_percent(gdal_ds=row[1], valid_value=0) # Index is row[0], then passed columns
    # vp = valid_percent_clip(AOI_PATH, row[1]) # Index is row[0], then passed columns
    dems.loc[row.Index, VALID_PERC] = vp


# dems[VALID_PERC] = dems[fields['BITMASK']].apply(lambda x: valid_percent(x, valid_value=0),)
                                                # meta=(VALID_PERC, float))
logger.info('Apply fxn done.')

# x = dems.compute()
logger.info('Compute done.')


