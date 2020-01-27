# -*- coding: utf-8 -*-
"""
Created on Mon May  6 13:32:12 2019

@author: disbr007
"""

from shapely.geometry import Point, Polygon, mapping
import fiona
from fiona.crs import from_epsg
import argparse


def points2bb(corner1, corner2, out_path):
    # Input corners
    corners_raw = [corner1, corner2]
    corners = []
    for corner in corners_raw:
        corner_y, corner_x = corner.split(', ')
        corner_y = float(corner_y.strip(' '))
        corner_x = float(corner_x.strip(' '))
        corner = (corner_y, corner_x)
        corners.append(corner)

    min_x = corners[0][0] # Get a min and max to start
    min_y = corners[0][1]
    max_x = corners[0][0]
    max_y = corners[0][0]

    for corner in corners:
        if corner[0] < min_x:
            min_x = corner[0]
        if corner[1] < min_y:
            min_y = corner[1]
        if corner[0] > max_x:
            max_x = corner[0]
        if corner[1] > max_y:
            max_y = corner[1]

    points = [Point(min_y, min_x), Point(min_y, max_x), Point(max_y, max_x), Point(max_y, min_x)]

    # Write four points as polygon geometry
    coords = [(p.x, p.y) for p in points]
    poly = Polygon(coords)
    
    # Write shapefile
    schema = {'geometry': 'Polygon', 'properties': {'id': 'int'},}
    crs = from_epsg(4326)
    driver = 'ESRI Shapefile'
#    out_path = r'C:\temp\bb_test3.shp'
#    print(out_path)
    
    with fiona.open(out_path, 'w', driver=driver, schema=schema, crs=crs) as shp:
        shp.write({
                'geometry': mapping(poly),
                'properties': {'id': 1},
        })

#points2bb("58.8178, 103.8625", "55.57504, 109.61839", r'C:\temp\bb_test3.shp')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('corner1', type=str, help='First corner of bounding box (lat, lon)')
    parser.add_argument('corner2', type=str, help='Second corner of bounding box (lat, lon)')
    parser.add_argument('out_shp', type=str, help='Path to write polygon shapefile')
    args = parser.parse_args()
    corner1 = args.corner1
    corner2 = args.corner2
    out_path = args.out_shp
    points2bb(corner1, corner2, out_path)
