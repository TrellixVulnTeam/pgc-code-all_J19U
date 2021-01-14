import argparse
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    geom_type_group = parser.add_mutually_exclusive_group(required=True)
    src_file_args = parser.add_argument_group('Source file args.')
    parser.add_argument('-o', '--out_lyr', type=os.path.abspath, required=True,
                        help='Path to write layer out to.')
    geom_type_group.add_argument('-p', '--point', nargs=2, action='append', type=float,
                                 help='Point to add: x y')
    geom_type_group.add_argument('-bb', '--bounding_box', nargs=4, action='append', metavar=('ulx, uly, lrx, lry'), type=float,
                                 help='Bounding box points: ulx, uly, lrx, lry')
    geom_type_group.add_argument('-f', '--src_file', type=os.path.abspath,
                                 help='Read coordinates from this file. '
                                      'lat_col and lon_col arguments are '
                                      'required with this flag.')

    src_file_args.add_argument('--lat_col',
                               help='Name of column holding latitudes.')
    src_file_args.add_argument('--lon_col',
                               help='Name of column holding longitudes.')

    parser.add_argument('--to_crs', type=str, help='Convert from WGS84 to this epsg code.')
    parser.add_argument('--crs', type=str, default='4326', help='CRS of point coordinates. Default: 4326')

    parser.add_argument('--out_drv', type=str, default='ESRI Shapefile',
                        help='Driver to use for out file. E.g. "GeoJSON"')

    args = parser.parse_args()

    coords = args.point
    bbs = args.bounding_box
    src_file = args.src_file

    crs = args.crs
    to_crs = args.to_crs

    lat_col = args.lat_col
    lon_col = args.lon_col

    out_lyr = args.out_lyr
    out_drv = args.out_drv

    if coords:
        points = [Point(x, y) for y, x in coords]

        gdf = gpd.GeoDataFrame(geometry=points, crs='epsg:{}'.format(crs))
        logger.info('Points read in: {}'.format(len(gdf)))
        logger.info(gdf)

    if bbs:
        boxes = [box(ulx, lry, lrx, uly) for ulx, lry, lrx, uly in bbs]
        logger.info([b.wkt for b in boxes])
        gdf = gpd.GeoDataFrame(geometry=boxes, crs='epsg:{}'.format(crs))

    if src_file:
        logger.info('Reading file: {}'.format(src_file))
        ext = Path(src_file).suffix
        if ext == '.csv':
            df = pd.read_csv(src_file)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(src_file)
        else:
            logger.error('Unknown source file extension: {}'.format(ext))

        df['geometry'] = df.apply(lambda x: Point(x[lon_col], x[lat_col]),
                                  axis=1)
        gdf = gpd.GeoDataFrame(df, geometry='geometry',
                               crs='epsg:{}'.format(crs))
        logger.info('\n{}'.format(gdf))

    if to_crs:
        gdf = gdf.to_crs('epsg:{}'.format(to_crs))

    logger.info('Creating file at: {}'.format(out_lyr))
    gdf.to_file(out_lyr, driver=out_drv)
