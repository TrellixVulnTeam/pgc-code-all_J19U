import argparse
import os
from pathlib import Path

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')

def split_shp(shp_p, field, out_dir):
    shp_p = Path(shp_p)
    out_dir = Path(out_dir)

    logger.info('Reading source file: {}'.format(shp_p))
    gdf = gpd.read_file(shp_p)

    logger.info('Splitting features based on {} to: {}'.format(field, out_dir))
    for i, row in tqdm(gdf.iterrows(), total=len(gdf)):
        row_gdf = gpd.GeoDataFrame([row], crs=gdf.crs)
        out_path = out_dir / '{}_{}{}'.format(shp_p.stem, row[field], shp_p.suffix)
        if not out_path.exists():
            row_gdf.to_file(out_path)

    logger.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input_shp', type=os.path.abspath,
                        help='Path to features to split.')
    parser.add_argument('-f', '--field', type=str,
                        help='Name of field to split based on.')
    parser.add_argument('-od', '--out_dir', type=os.path.abspath,
                        help='Path to directory to write split features to.')

    args = parser.parse_args()

    split_shp(args.input_shp, args.field, args.out_dir)
