# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 16:43:27 2019

@author: disbr007
"""


def range_tuples(start, stop, step):
    
    ranges = []
    lr = range(start, stop+step, step)
    for i, r in enumerate(lr):
        if i < len(lr)-1:
            ranges.append((r, lr[i+1]))
            
    return ranges

    
def lat_lon_cells(lat_step, lon_step):
    '''
    Splits the globe into cells with size lat_step x lon_step
    '''
    
    lats = range_tuples(-90, 90, lat_step)
    lons = range_tuples(-180, 180, lon_step)

    cells = []
    for min_lat, max_lat in lats:
        for min_lon, max_lon in lons:
            cells.append((min_lon, min_lat, max_lon, max_lat))
            
    return cells


cells = lat_lon_cells(30, 90)

def write_bbs(cells):
    '''
    takes a list of tuples of coordinates and writes them as a polygon
    cells: list of tuples of (min_lon, min_lat, max_lon, max_lat)
    '''
    try:
        from shapely.geometry import Point, Polygon, mapping
        import fiona
        from fiona.crs import from_epsg
        for cell in cells:
            min_lat, max_lat = cell[1], cell[3]
            min_lon, max_lon = cell[0], cell[2]
            
            points = [Point(min_lon, min_lat), Point(min_lon, max_lat), Point(max_lon, max_lat), Point(max_lon, min_lat)]
            
            # Write four points as polygon geometry
            coords = [(p.x, p.y) for p in points]
            poly = Polygon(coords)
            
            # Write shapefile
            schema = {'geometry': 'Polygon', 
                      'properties': {'id': 'int', 'corners': 'str'}}
            crs = from_epsg(4326)
            driver = 'ESRI Shapefile'
            out_path = r'C:\temp\mfp_slice_bb.shp'
            if os.path.exists(out_path):
                os.remove(out_path)
            try:
                with fiona.open(out_path, 'a', driver=driver, schema=schema, crs=crs) as shp:
                    shp.write({
                        'geometry': mapping(poly),
                        'properties': {'id': 1, 'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon)}
                })
            except OSError:
                with fiona.open(out_path, 'w', driver=driver, schema=schema, crs=crs) as shp:
                    shp.write({
                            'geometry': mapping(poly),
                            'properties': {'id': 1, 'corners': '({},{}) ({},{})'.format(min_lat, min_lon, max_lat, max_lon)},
                    })
    except ImportError as e:
        print(e)
        print("Skipped writing bounding boxes due to missing modules.")

    
    
    
    
    