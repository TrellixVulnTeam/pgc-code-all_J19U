import argparse
import os

import geopandas as gpd


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input_vector', type=os.path.abspath,
                        help='Path to vector file to list fields in.')
    parser.add_argument('-d', '--driver', type=str,
                        help='Driver to use to open input.')
    parser.add_argument('-t', '--data_type', action='store_true',
                        help='Use to also print datatypes of each field.')

    args = parser.parse_args()

    gdf = gpd.read_file(args.input_vector, driver=args.driver)

    for f in list(gdf):
        print(f)

    if args.data_type:
        print(gdf.dtypes)
