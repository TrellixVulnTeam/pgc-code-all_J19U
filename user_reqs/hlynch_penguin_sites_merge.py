import os
import glob
from pathlib import Path

from tqdm import tqdm
import pandas as pd
import geopandas as gpd


shp_dir = Path(r'V:\pgc\data\scratch\jeff\deliverables\hlynch\scratch\PlanetAOI_4326')

shps = shp_dir.glob('*shp')

adelies = []
chinstraps = []
for s in shps:
    if len(s.stem) == 4:
        adelies.append(s)
    else:
        chinstraps.append(s)

adelies_gdf = gpd.GeoDataFrame()
for shp in tqdm(adelies):
    site_gdf = gpd.read_file(shp)
    site_gdf['site_name'] = shp.stem
    adelies_gdf = pd.concat([adelies_gdf, site_gdf])

chinstraps_gdf = gpd.GeoDataFrame()
for shp in tqdm(chinstraps):
    site_gdf = gpd.read_file(shp)
    site_gdf['site_name'] = shp.stem
    chinstraps_gdf = pd.concat([chinstraps_gdf, site_gdf])


adelies_gdf.to_file(shp_dir / 'adelies_sites.shp')
chinstraps_gdf.to_file(shp_dir / 'chinstrap_sites.shp')