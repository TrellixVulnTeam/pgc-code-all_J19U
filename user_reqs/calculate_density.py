# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 08:46:36 2019

@author: disbr007
"""

import argparse
import copy
import logging
from pathlib import Path
import warnings

import pandas as pd
import geopandas as gpd
from shapely.geometry import box

# To ignore pandas warning about joining with multi-indexes
warnings.simplefilter(action='ignore', category=UserWarning)

# Logging
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                              '%(message)s')
logger.setLevel('INFO')
sh = logging.StreamHandler()
sh.setLevel('INFO')
sh.setFormatter(formatter)
logger.addHandler(sh)


def get_count(geocells, fps, centroid=False, count_field='count',
              date_col=None):
    '''
    Gets the count of features in fps that intersect with each feature
    in geocells. This method is essentially a many to many spatial join,
    so if two footprints overlaps a grid cell, there will be two of that
    grid cell in the resulting dataframe. These repeated cells are then
    counted and saved to the returned dataframe

    Parameters
    ----------
    geocells: gpd.GeoDataFrame
        Geodataframe of features to count within. This can be any
        polygon GeoDataFrame.
    fps: gpd.GeoDataFramegeo
        Dataframe of polygons to be counted.
    centroid : bool
        Count footprint only if it's centroid falls within the geocell.
    count_field : str
        Name of field to add to geocells to place counts in
    date_col : str
        Name of an existing field in fps that contains dates. If provided,
        the minimum date and maximum date of the footprints that overlap
        each grid cell will be recorded.

    Returns
    ----------
    gpd.GeoDataFrame : geocells with added count column.
    '''
    # Confirm crs is the same
    logger.info('Counting footprints over each feature...')
    if geocells.crs != fps.crs:
        logger.info('Converting crs of grid to match footprint...')
        geocells = geocells.to_crs(fps.crs)

    logger.info('Performing spatial join...')
    # Get a column from fps to use to test if sjoin found matches
    fp_col = fps.columns[0]
    if centroid:
        sj = gpd.sjoin(geocells, fps.set_geometry(fps.centroid), how='left',
                       op='intersects')
    else:
        sj = gpd.sjoin(geocells, fps, how='left', op='intersects')
    sj.index.name = count_field
    sj.reset_index(inplace=True)

    # Remove no matches, group the rest, counting the index, and get minimum
    # and maximum dates if requested
    logger.info('Getting count...')
    agg = {count_field: 'count'}
    if date_col:
        agg[date_col] = ['min', 'max']

    gb = sj[~sj[fp_col].isna()].groupby(count_field).agg(agg)

    ## Join geocells to dataframe with counts
    out = pd.merge(geocells, gb, left_index=True, right_index=True,
                   how='outer')

    if date_col:
        # If date aggregation was done, count column will be tuple:
        # (count_field: 'count') due to multi-index in gb, so rename back to
        # just count_field
        out.rename(columns={(count_field, 'count'): count_field}, inplace=True)

    # Replace NaN with 0
    out[count_field] = out[count_field].fillna(0)

    out = gpd.GeoDataFrame(out, geometry=out.geometry, crs=geocells.crs)

    return out


def calculate_density(grid_path, footprint_path, out_path=None,
                      check_overlap=False,
                      centroid=False,
                      count_field='count',
                      date_col=None):
    """
    Wrapper around get_count to read inputs and write the out file.

    Parameters
    ----------
    grid_path : str
        Path to the vector-file of polygon areas to use for counting.
    footprint_path : str
        Path to the vector file of polygons to be counted.
    out_path : str
        Path to write the grid with added count field to.
    check_overlap : bool
        True to first remove any footprints that do not intersect the grid
        before counting. This can speed operations where numerous footprints
        are provided that are not over the grid cells.
    centroid : bool
        True to use the centroid of the footprints when counting.
    date_col : str
        The name of an existing date field in footprints. If provided the
        minimum and maximum footprint dates for each grid cell will be
        recorded.

    Returns
    --------
    gpd.GeoDataFrame grid with count_field and counts added
    """
    # Read data
    if isinstance(grid_path, gpd.GeoDataFrame):
        grid = copy.deepcopy(grid_path)
    else:
        logger.info('Loading grid...')
        if 'gdb' in grid_path:
            gdb = Path(grid_path).parent
            layer = Path(grid_path).name
            grid = gpd.read_file(gdb, layer=layer)
        else:
            grid = gpd.read_file(grid_path)
    logger.info('Features in grid: {:,}'.format(len(grid)))

    if isinstance(footprint_path, gpd.GeoDataFrame):
        footprint = copy.deepcopy(footprint_path)
    else:
        logger.info('Loading footprints...')
        if check_overlap:
            logger.info('(only loading footprints in grid bounding box)')
            bbox = box(*grid.total_bounds)
            # bbox = None
        else:
            bbox = None
        if str(Path(footprint_path).parent).endswith('.gdb'):
            gdb = Path(footprint_path).parent
            layer = Path(footprint_path).name
            footprint = gpd.read_file(gdb, layer=layer, bbox=bbox)
        else:
            footprint = gpd.read_file(footprint_path, bbox=bbox)
    logger.info('Features in footprint: {:,}'.format(len(footprint)))

    if check_overlap:
        # Reduce to only footprints that overlap grid cells.
        logger.info('Removing any non-overlapping footprints...')
        footprint = footprint[footprint.index.isin(
            gpd.overlay(footprint, grid).index)]
        logger.info('Remaining footprints: {:,}'.format(len(footprint)))

    logger.info('Calculating density...')
    density = get_count(grid, footprint,
                        centroid=centroid,
                        count_field=count_field,
                        date_col=date_col)

    # Convert any tuple columns to strings (occurs with aggregating-ing same
    # column multiple ways, i.e. if date_col was provided)
    density.columns = [str(x) if type(x) == tuple else x
                       for x in density.columns]
    if out_path:
        logger.info('Writing density to: {}'.format(out_path))
        density.to_file(out_path)
        
    return density


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        "Count the number of footprints that occur within each polygon of the "
        "input_grid. Both input_footprint and input_grid must be polygons and "
        "either shapefiles or feature classes in file geodatabases. The "
        "input_grid can be created using QGIS's 'Vector Grid' or ArcMap's "
        "'Create Fishnet' tool or similar."
        "\n\n"
        "If using file geodatabases, specify as:\n "
        "the_geodatabase.gdb\\the_feature_class\nor\n"
        "the_geodatabase.gdb/the_feature_class\n"
        "\n"
        "The output will be the input_grid, with an added field "
        "(--count_field) containg the number of input_footprint polygons in "
        "each input_grid polygon. Writing to file geodatabases is not "
        "supported."
        "The input coordinate systems will be checked to ensure they are the "
        "same and the footprint will be reprojected to match the grid if "
        "they are not, however, it is recommend to pass inputs with a commmon " 
        "coordinate system."
        
        "\n")

    parser.add_argument('-g', '--input_grid', type=str, required=True,
                        help='Grid to count density on.')
    parser.add_argument('-f', '--input_footprint', type=str, required=True,
                        help='Footprint to calculate density of.')
    parser.add_argument('-o', '--out_path', type=str, required=True,
                        help='Path to write the density shapefile.')
    parser.add_argument('--use_centroid', action='store_true',
                        help='Use the centroid of each footprint, when '
                             'counting. This will be faster than using the '
                             'footprint and also result in each footprint '
                             'only being counted once.')
    parser.add_argument('--check_overlap', action='store_true',
                        help='Remove footprints that do not intersect any '
                             'grid cells before performing spatial join. This '
                             'can speed operations where there are a large '
                             'number of footprints that fall outside the '
                             'grid.')
    parser.add_argument('--count_field', type=str, default='count',
                        help='The name of the field to create that will hold '
                             'the counts.')
    parser.add_argument('--date_col', type=str,
                        help='Column in input footprint holding dates '
                             'to return min and max dates.')

    args = parser.parse_args()

    grid_path = args.input_grid
    footprint_path = args.input_footprint
    out_path = args.out_path
    centroid = args.use_centroid
    check_overlap = args.check_overlap
    count_field = args.count_field
    date_col = args.date_col

    calculate_density(grid_path=grid_path,
                      footprint_path=footprint_path,
                      out_path=out_path,
                      centroid=centroid,
                      check_overlap=check_overlap,
                      count_field=count_field,
                      date_col=date_col)
