import copy
import operator
from random import randint
from tqdm import tqdm

import numpy as np
from osgeo import ogr, gdal
import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.RasterWrapper import Raster

# Suppress pandas SettingWithCopyWarning
pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'INFO')

nebs_fld = 'neighbors'
area_fld = 'area'


def _weighted_mean(series, value_fld, weight_fld=area_fld,
                   out_fld='weighted_mean'):
    d = {}
    d[out_fld] = (series[value_fld] * series[weight_fld]).mean()
    return pd.Series(d, index=out_fld)


class ImageObjects:
    """
    Designed to facilitate object-based-image-analysis
    classification.
    """
    def __init__(self, objects_path):
        if isinstance(objects_path, gpd.GeoDataFrame):
            self.objects = copy.deepcopy(objects_path)
        else:
            self.objects_path = objects_path
            self.objects = gpd.read_file(objects_path)

        self.num_objs = len(self.objects)
        self.fields = list(self.objects.columns)

        # Field name for area
        if area_fld not in self.fields:
            self.area_fld = area_fld
        # Define field name to hold neighbors
        if nebs_fld not in self.fields:
            self.nebs_fld = nebs_fld
        # Create empty field to hold neighbors
        self.objects[self.nebs_fld] = np.NaN

        # TODO: check for unique index, create if not
        # Name index if unnamed
        if not self.objects.index.name:
            self.objects.index.name = 'index'
        if not self.objects.index.is_unique:
            logger.warning('Non-unique index not supported.')

    def compute_area(self):
        self.objects[self.area_fld] = self.objects.geometry.area
        self.fields.append(self.area_fld)

    def get_value(self, index_value, value_field):
        if value_field not in self.fields:
            logger.error('Field not found: {}'.format(value_field))
            logger.error('Cannot get value for field: {}'.format(value_field))
            raise KeyError

        value = self.objects.at[index_value, value_field]
        return value

    def get_neighbors(self, subset):
        """Creates a new column containing IDs of neighbors as list of indicies."""
        # If no subset is provided, use the whole dataframe
        if subset is None:
            logger.warning('No subset provided when finding neighbors, '
                           'computation may be slow.')
            subset = copy.deepcopy(self.objects)

        # List to store neighbors
        ns = []
        # List to store unique_ids
        labels = []
        # Iterate over rows, for each row, get indicies of all features it touches
        logger.debug('Getting neighbors for {} features...'.format(len(subset)))
        # TODO: Make apply function?
        for index, row in tqdm(subset.iterrows(),
                               total=len(subset),
                               desc='Finding neighbors'):
            neighbors = self.objects[self.objects.geometry.touches(row['geometry'])].index.tolist()
            # If the feature is considering itself a neighbor remove it from the list
            if index in neighbors:
                neighbors = neighbors.remove(index)

            # Save the neighbors that have been found and their IDs
            ns.append(neighbors)
            labels.append(index)

        if not any(ns):
            logger.warning('No neighbors found.')
        # Create data frame of the unique ids and their neighbors
        nebs = pd.DataFrame({self.objects.index.name: labels, self.nebs_fld: ns}) \
            .set_index(self.objects.index.name, drop=True)

        # Combine the neighbors dataframe back into the main dataframe, joining on unique_id -
        # essentially just adding the neighbors column back to subset
        self.objects.update(nebs)
        # self.objects = pd.merge(nebs, self.objects,
        #                         how='outer', suffixes=('', '_y'),
        #                         left_index=True, right_index=True)

        logger.debug('Neighbor computation complete.')

        return self.objects[self.objects.index.isin(subset.index)]

    def neighbor_features(self, subset=None):
        """
        Create a new geodataframe of neighbors (geometries and values)
         for all features in subset. Finds neighbors if self.nebs_fld
         does not exist already.

        Parameters
        ----------
        subset : gpd.GeoDataFrame, optional
            Subset of self.objects containing only features to find neighbors for. The default is None.

        Returns
        -------
        neighbor_feats : gpd.GeoDataFrame
            GeoDataFrame containing one row per neighbor for each row in subset. Will contain
            repeated geometries if features in subset share neighbors.

        """
        neb_src_fld = 'neighbor_src'
        neb_id_fld = 'neighbor_id'

        # Compute for entire dataframe if subset is not provided.
        if not isinstance(subset, (gpd.GeoDataFrame, pd.DataFrame)):
            # TODO: Turn subset into an ImageObjects, then get subset.objects
            # SubObjects = copy.deepcopy(self)
            subset = copy.deepcopy(self.objects)

        # Find neighbors if column containing neighbor IDs does not already exist
        if self.nebs_fld not in subset.columns:
            self.get_neighbors(subset=subset)
            subset = self.objects[self.objects.index.isin(subset.index)]

        # Store source IDs and neighbor IDs from in lists
        source_ids = []
        neighbor_ids = []
        for index, row in tqdm(subset.iterrows(), desc='Getting neighbor features'):
            # Get all neighbors of current feature, as list, add to master list
            neighbors = row[self.nebs_fld]
            neighbor_ids.extend(neighbors)
            # Add source ID to list one time for each of its neighbors
            for n in neighbors:
                source_ids.append(index)

        # Create 'look up' dataframe of with one row for each source id and neighbor pair
        src_lut = pd.DataFrame({neb_src_fld: source_ids, neb_id_fld: neighbor_ids})

        # Find each neighbor feature in the master GeoDataFrame, creating a new GeoDataFrame
        neighbor_feats = gpd.GeoDataFrame()
        for ni in neighbor_ids:
            # feat = self.objects[self.objects[unique_id] == ni]
            feat = self.objects.loc[[ni]]
            neighbor_feats = pd.concat([neighbor_feats, feat])

        # Join neighbor features to sources
        # This is one-to-many with one row for each neighbor-source pair
        neighbor_feats = pd.merge(neighbor_feats, src_lut,
                                  left_index=True, right_on=neb_id_fld)
        # Remove redundant neighbor_id column - this is the same as the index in this df
        neighbor_feats.drop(columns=[neb_id_fld], inplace=True)

        return neighbor_feats

    def compute_neighbor_values(self, value_field, out_field, subset=None,):
        """Look up the value in value field for each neighbor,
        adding a dict of {neighbor_id: value} in out_field of
        each row (only performed on rows where neighbors have
        been computed previously)"""
        if subset is None:
            subset = self.objects
        # If subset doesn't have neighbors computed
        if any(subset[nebs_fld].isnull()):
            subset = self.get_neighbors(subset)
        # Get all neighbors that have been found in dataframe
        # This takes lists of neighbors and puts them into a Series,
        # drops NaN's and drops duplicates
        neighbors = pd.DataFrame(subset.neighbors.explode().
                                 dropna().
                                 drop_duplicates()).set_index(self.nebs_fld)
        # Get the value in value_field for each neighbor feature
        neighbors = pd.merge(neighbors, self.objects[[value_field]],
                             left_index=True, right_index=True)
        # Create a dictionary in the main objects dataframe
        # which is {neighbor_id: value} for all objects that
        # have neighbors computed
        # TODO: change to use get_value()
        subset[out_field] = (subset[~subset[self.nebs_fld].isnull()][self.nebs_fld]
                             .apply(lambda x: {i: neighbors.at[i, value_field] for i in x}))

        # Merge neighbor value field back in
        self.objects = pd.merge(self.objects, subset[[out_field]],
                                how='outer', suffixes=('', '_y'),
                                left_index=True, right_index=True)
        # self.objects[out_field] = (self.objects[~self.objects[self.nebs_fld].isnull()][self.nebs_fld]
        #                            .apply(lambda x: {i: neighbors.at[i, value_field] for i in x}))
        self.fields.append(out_field)

        return self.objects[self.objects.index.isin(subset.index)]

    def _merge_objects(self, feat_ids, merge_fld):
        dissolve_fld = 'dissolve_temp'
        to_merge = self.objects.loc[feat_ids]
        to_merge[dissolve_fld] = 1
        merged = to_merge.dissolve(by=dissolve_fld, aggfunc=lambda x: _weighted_mean(x, merge_fld))

        # Drop original features from self.objects
        self.objects.drop([feat_ids])
        # Put merged features back in

    def merge_adj(self, merge_until_fld, merge_until_op, merge_until_stop,
                  merge_on_fld, merge_thresh, ascending_area=True, recompute_area=False):
        """Merge features based on closest neighbor value if
        difference between feature value and neighbor value is
        within merge thresh.
        Parameters
        --------
        merge_until_fld : str
            Field in self.objects to identify features to merge
        merge_until_op : operator function
            Operator function to use to compare merge_until_fld to
            merge_until_stop
        merge_until_stop : str/int/float/bool
            Value in merge_until_field to end merging when
            merge_until_op(merge_until_fld, merge_until_stop) == True
        merge_on_fld : str
            Field in self.objects to merge based on values in
        merge_thresh : str/int/float/bool
            Threshold that neighbor value must be within compared
            to feature value to merge
        ascending_area : bool
            Sort by area, then merge.
        recompute_area : bool
            Recompute areas before sorting or merging - useful after
            previous merges have taken place."""
        # Field names
        neighbor_value_fld = '{}_neb_values'.format(merge_on_fld)
        merge_candidates_fld = 'merge_candidates'
        skip_fld = 'skip'

        # if neighbor_value_fld not in self.objects.columns or any(self.objects[neighbor_value_fld].isnull()):
        #     self.compute_neighbor_values(value_field=merge_on_fld,
        #                                  out_field=neighbor_value_fld)
        # Get all features to merge
        to_merge = self.objects[~merge_until_op(self.objects[merge_until_fld], merge_until_stop)]

        # Get neighbors value for features to merge if not already
        if neighbor_value_fld not in to_merge.columns or any(to_merge[self.nebs_fld].isnull()):
            to_merge = self.compute_neighbor_values(merge_on_fld, out_field=neighbor_value_fld, subset=to_merge)

        # Find closest neighbor
        # Find all neighbors within threshold
        to_merge[merge_candidates_fld] = (to_merge
                                          .apply(lambda x: {fid: val for fid, val in x[neighbor_value_fld].items() if
                                                            x[merge_on_fld]-merge_thresh
                                                            <= val
                                                            <= x[merge_on_fld]+merge_thresh}, axis=1))
        # Mark objects with no candidates as skippable

        to_merge[skip_fld] = to_merge[merge_candidates_fld].apply(lambda x: len(x) == 0)

        # Sort by area (if specified) so merging will start with smallest features
        if recompute_area:
            self.compute_area()
        elif self.area_fld not in self.fields or any(self.objects[self.area_fld].isnull()):
            self.compute_area()
        self.objects.sort_values(by=self.area_fld, ascending=ascending_area, inplace=True)

    def determine_adj_thresh(self, neb_values_fld, value_thresh, value_op, out_field, subset=None):
        """Determines if each row is has neighbor that meets that value threshold provided, used
        for classifying.

        Parameters
        ---------
        neb_values_fld : str
            Field containing dict of {neighbor_id: value}
        value_thresh : str/int/float/bool
            The value to compare each neighbors value to.
        value_op : operator function
            From operator library, the function to use to compare neighbor value to value_thresh:
            operator.le(), operator.gte(), etc.
        out_field : str
            Field to create in self.objects to store result of adjacency test.

        Returns
        --------
        None : modifies self.objects in place
        """
        # For all rows where neighbor_values have been computed, compare neighbor values to
        # value_thresh using the given value_op. If any are True, True is returned
        self.objects[out_field] = (self.objects[~self.objects[neb_values_fld].isnull()][neb_values_fld]
                                   .apply(lambda x: any(value_op(v, value_thresh) for v in x.values())))

obj_path = r'E:\disbr007\umn\2020sep27_eureka\seg' \
           r'\WV02_20140703013631_1030010032B54F00_' \
           r'14JUL03013631-M1BS-500287602150_01_P009_' \
           r'u16mr3413_pansh_test_aoi_sr5_rr100x0_ms100_' \
           r'tx500_ty500.shp'

o = ImageObjects(obj_path)
# o.compute_neighbor_values('meanB0', 'neb_meanB0', subset=o.objects.loc[[i for i in range(0, 15)]])
o.compute_area()
o.merge_adj(area_fld, operator.gt, 26.2,
            merge_on_fld='meanB0', merge_thresh=250, recompute_area=True)

# o.objects = o.objects.loc[[2, 3, 4]]

