import os
import argparse

import geopandas as gpd
from shapely.geometry import Point, box

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    geom_type_group = parser.add_mutually_exclusive_group(required=True)
    geom_type_group.add_argument('-p', '--point', nargs=2, action='append', metavar=('x', 'y'), type=float,
                                 help='Point to add: x y')
    geom_type_group.add_argument('-bb', '--bounding_box', nargs=4, action='append', metavar=('ulx, uly, lrx, lry'), type=float,
                                 help='Bounding box points: ulx, uly, lrx, lry')
    parser.add_argument('--to_crs', type=str, help='Convert from WGS84 to this epsg code.')
    parser.add_argument('--crs', type=str, default='4326', help='CRS of point coordinates. Default: 4326')
    parser.add_argument('-o', '--out_lyr', type=os.path.abspath, required=True,
                        help='Path to write layer out to.')
    parser.add_argument('--out_drv', type=str, default='ESRI Shapefile',
                        help='Driver to use for out file. E.g. "GeoJSON"')

    args = parser.parse_args()

    coords = args.point
    bbs = args.bounding_box
    crs = args.crs
    to_crs = args.to_crs
    out_lyr = args.out_lyr
    out_drv = args.out_drv

    if coords:
        points = [Point(y, x) for x, y in coords]

        gdf = gpd.GeoDataFrame(geometry=points, crs='epsg:{}'.format(crs))
        print('Points read in: {}'.format(len(gdf)))
        print(gdf)

    if bbs:
        boxes = [box(ulx, lry, lrx, uly) for ulx, lry, lrx, uly in bbs]
        print([b.wkt for b in boxes])
        gdf = gpd.GeoDataFrame(geometry=boxes, crs='epsg:{}'.format(crs))

    if to_crs:
        gdf = gdf.to_crs('epsg:{}'.format(to_crs))

    print('Creating file at: {}'.format(out_lyr))
    gdf.to_file(out_lyr, driver=out_drv)
