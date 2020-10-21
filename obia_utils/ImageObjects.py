import copy
import operator
from random import randint
from tqdm import tqdm

import numpy as np
from osgeo import ogr, gdal
import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import write_gdf
from misc_utils.RasterWrapper import Raster

import matplotlib.pyplot as plt
plt.style.use('pycharm')

# Suppress pandas SettingWithCopyWarning
pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'INFO')

nebs_fld = 'neighbors'
area_fld = 'area'

#%%
def weighted_mean(values, weights):
    weight_proportions = [i / sum(weights) for i in weights]
    wm = sum([v * w for v, w in zip(values, weight_proportions)])

    return wm


def weighted_majority(values, weights):
    weighted_values = [(v, w) for v, w in zip(values, weights)]
    wmaj = max(weighted_values, key=operator.itemgetter(1))
    return wmaj


class ImageObjects:
    """
    Designed to facilitate object-based-image-analysis
    classification.
    """
    def __init__(self, objects_path):
        if isinstance(objects_path, gpd.GeoDataFrame):
            self.objects = copy.deepcopy(objects_path)
            self.objects_path = None
        else:
            self.objects_path = objects_path
            self.objects = gpd.read_file(objects_path)

        self.num_objs = len(self.objects)
        self._fields = list(self.objects.columns)

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

    @property
    def fields(self):
        self._fields = list(self.objects.columns)
        return self._fields

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

    def get_neighbors(self, subset=None):
        """Creates a new column containing IDs of neighbors as list of
        indicies."""
        # If no subset is provided, use the whole dataframe
        if subset is None:
            logger.warning('No subset provided when finding neighbors, '
                           'computation may be slow.')
            subset = copy.deepcopy(self.objects)

        # List to store neighbors
        ns = []
        # List to store unique_ids
        labels = []
        # Iterate over rows, for each row, get indicies of all features
        # it touches
        logger.debug('Getting neighbors for {} '
                     'features...'.format(len(subset)))
        # TODO: Make apply function?
        for index, row in tqdm(subset.iterrows(),
                               total=len(subset),
                               desc='Finding neighbors'):
            neighbors = self.objects[self.objects.geometry
                                     .touches(row['geometry'])].index.tolist()
            # If the feature is considering itself a neighbor remove it from
            # the list
            if index in neighbors:
                neighbors = neighbors.remove(index)

            # Save the neighbors that have been found and their IDs
            ns.append(neighbors)
            labels.append(index)

        if not any(ns):
            logger.warning('No neighbors found.')
        # Create data frame of the unique ids and their neighbors
        nebs = pd.DataFrame({self.objects.index.name: labels,
                             self.nebs_fld: ns}).set_index(self.objects.
                                                           index.name,
                                                           drop=True)

        # Combine the neighbors dataframe back into the main dataframe
        self.objects.update(nebs)

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
            Subset of self.objects containing only features to find neighbors
            for. The default is None, and will use the entire self.objects

        Returns
        -------
        neighbor_feats : gpd.GeoDataFrame
            GeoDataFrame containing one row per neighbor for each row in
            subset. Will contain repeated geometries if features in subset
            share neighbors.
        """
        neb_src_fld = 'neighbor_src'
        neb_id_fld = 'neighbor_id'

        # Compute for entire dataframe if subset is not provided.
        if not isinstance(subset, (gpd.GeoDataFrame, pd.DataFrame)):
            # TODO: Turn subset into an ImageObjects, then get subset.objects
            # SubObjects = copy.deepcopy(self)
            subset = copy.deepcopy(self.objects)

        # Find neighbors if column containing neighbor IDs does not already
        # exist
        if self.nebs_fld not in subset.columns:
            self.get_neighbors(subset=subset)
            subset = self.objects[self.objects.index.isin(subset.index)]

        # Store source IDs and neighbor IDs from in lists
        source_ids = []
        neighbor_ids = []
        for index, row in tqdm(subset.iterrows(),
                               desc='Getting neighbor features'):
            # Get all neighbors of current feature, as list, add to master list
            neighbors = row[self.nebs_fld]
            neighbor_ids.extend(neighbors)
            # Add source ID to list one time for each of its neighbors
            for n in neighbors:
                source_ids.append(index)

        # Create 'look up' dataframe of with one row for each source id and
        # neighbor pair
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
        # Remove redundant neighbor_id column - this is the same as the index
        # in this df
        neighbor_feats.drop(columns=[neb_id_fld], inplace=True)

        return neighbor_feats

    def compute_neighbor_values(self, value_field, out_field=None, subset=None,):
        """Look up the value in value field for each neighbor,
        adding a dict of {neighbor_id: value} in out_field of
        each row (only performed on rows where neighbors have
        been computed previously)"""
        if not out_field:
            out_field = 'nv_{}'.format(value_field)
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
                             left_index=True, right_index=True,
                             )
        # Create a dictionary in the main objects dataframe
        # which is {neighbor_id: value} for all objects that
        # have neighbors computed
        # TODO: change to use get_value()
        subset[out_field] = (subset[~subset[self.nebs_fld].isnull()][self.nebs_fld]
                             .apply(lambda x: {i: neighbors.at[i, value_field] for i in x}))

        # Merge neighbor value field back in
        self.objects = pd.merge(self.objects.drop(columns=out_field),
                                subset[[out_field]],
                                how='outer', suffixes=('', '_y'),
                                left_index=True, right_index=True)

        return self.objects[self.objects.index.isin(subset.index)]

    def find_merge_candidates(self, fields_ops_thresholds):
        """Marks columns that meet merge criteria (field op threshold)
        as True in merge_candidates field.
        fields_ops_thresholds.
        Parameters
        ---------
        fields_ops_thresholds : list
            List of tuples of (field_name, operator fxn, threshold)

        Returns
        ------
        None : updates self.objects in place"""
        df = pd.DataFrame(
            [op(self.objects[field], threshold) for field, op, threshold in
             fields_ops_thresholds]).transpose()

        self.objects[merge_candidates] = df.all(axis='columns')

    def pseudo_merging(self, merge_field, merge_criteria, pairwise_criteria):
        logger.info('Beginning pseudo-merge to determine merges...')
        # Get objects that meet merge criteria
        self.find_merge_candidates(merge_criteria)

        # Sort merge candidates
        # TODO: sort merge candidates

        self.objects[mergeable] = True
        self.objects[merge_path] = [[] for i in range(len(self.objects))]

        # Dataframe to hold objects that will be merged later
        to_be_merged = gpd.GeoDataFrame()
        # While there are rows that are merge_candidates, that haven't been
        # checked
        while self.objects[[merge_candidates, mergeable]].all(
                axis='columns').any():
            # Get the first row that is a merge_candidate and marked mergeable
            r = (self.objects[self.objects[merge_candidates] &
                             self.objects[mergeable]].iloc[0])
            # Get ID of row
            i = r.name
            print(i)
            if not r[merge_nv_field]:
                self.objects.at[i, mergeable] = False
                continue

            # Find best match, which is closest value in merge field, given
            # pairwise criteria are all met
            best_match = None
            # Sort merge_field neighbor values by difference in merge_field to
            # current feature's merge_field value (start with closest neighbor
            # value in merge_field)
            nvs = sorted(r[merge_nv_field].items(),
                         key=lambda y: abs(r[merge_field] - y[1]))
            for nv in nvs:
                possible_match = self.objects.loc[nv[0], :]
                if pairwise_match(r, possible_match, pairwise_criteria):
                    best_match = possible_match
                    break

            if best_match is not None:
                print('match')
                best_match_id = best_match.name
                # pseudo merge
                # Handle other objects that are neighbors
                for neighbor in r[nebs_fld]:
                    # Remove current row from it's neighbors lists of
                    # neighbors
                    while i in self.objects.at[neighbor, nebs_fld]:
                        self.objects.at[neighbor, nebs_fld].remove(i)
                    # Add new (best_match_id) ID to neighbors list of neighbors
                    # if it wasn't already a neighbor
                    if neighbor != best_match_id:
                        if best_match_id not in self.objects.at[
                            neighbor, nebs_fld]:
                            self.objects.at[neighbor, nebs_fld].append(
                                best_match_id)
                    # Remove current feature from all of its neighbor's
                    # neighbor value fields
                    while i in self.objects.at[neighbor, merge_nv_field]:
                        self.objects.at[neighbor, merge_nv_field].pop(i)
                # Update value fields with approriate aggregate,
                # e.g.: weighted mean
                for vf, agg_type in value_fields:
                    if agg_type == 'mean':
                        self.objects.at[best_match_id, vf] = (
                            weighted_mean(values=[r[vf], best_match[vf]],
                                          weights=[r[area_fld],
                                                   best_match[area_fld]]))
                    elif agg_type == 'majority':
                        # Get the value assoc with object that has most area
                        self.objects.at[best_match_id, vf] = (
                            max([(r[vf], r[area_fld]),
                                 (best_match[vf], best_match[area_fld])],
                                key=operator.itemgetter(1))[0])
                    elif agg_type == 'minority':
                        # Get the value assoc. with object that has least area
                        self.objects.at[best_match_id, vf] = (
                            min([(r[vf], r[area_fld]),
                                 (best_match[vf], best_match[area_fld])],
                                key=operator.itemgetter(1))[0])
                    elif agg_type == 'minimum':
                        self.objects.at[best_match_id, vf] = min(
                            r[vf], best_match[vf])
                    elif agg_type == 'maximum':
                        self.objects.at[best_match_id, vf] = max(
                            r[vf], best_match[vf])
                    else:
                        logger.error('Unknown agg_type: {} for '
                                     'value field: {}'.format(agg_type, vf))
                # Update area field (add areas)
                self.objects.at[best_match_id, area_fld] = (r[area_fld] +
                                                            best_match[area_fld])

                # Update merge_path
                # Store id to merge in new (best_match) object's merge_path
                # field
                self.objects.at[best_match_id, merge_path].append(i)
                # Get all of the feature to be merged's merge_path ids and add
                # them
                self.objects.at[best_match_id, merge_path].extend(r[merge_path])

                # Copy features that will be merged to temp gdf
                to_be_merged = pd.concat([to_be_merged, gpd.GeoDataFrame([r])])
            else:
                print('no match')

            # Mark feature as no longer mergeable - either it was psuedo-merged
            # or else it had no best match
            self.objects.at[i, mergeable] = False
            self.find_merge_candidates(merge_criteria)

        # zero
        # merge features that have a merge path
        logger.info('Performing calculated merges...')
        for i, r in self.objects[
                self.objects[merge_path].map(lambda d: len(d)) > 0].iterrows():
            # Create gdf of current row and the features to merge with it.
            # Important that the current row is first, as it contains the
            # correct aggregated values and the dissolve function defaults
            # to keeping the first rows values
            to_merge = pd.concat([gpd.GeoDataFrame([r]), to_be_merged[
                to_be_merged.index.isin(r[merge_path])]])
            to_merge['temp'] = 1
            to_merge = to_merge.dissolve(by='temp')
            to_merge.index = [i]
            to_merge.drop(columns='temp', inplace=True)

            self.objects.drop(r[merge_path] + [i], inplace=True)
            self.objects = pd.concat([self.objects, to_merge])

    def determine_adj_thresh(self, neb_values_fld, value_thresh, value_op, out_field, subset=None):
        """Determines if each row is has neighbor that meets the value
        threshold provided. Used for classifying.

        Parameters
        ---------
        neb_values_fld : str
            Field containing dict of {neighbor_id: value}
        value_thresh : str/int/float/bool
            The value to compare each neighbors value to.
        value_op : operator function
            From operator library, the function to use to compare neighbor
            value to value_thresh:
            operator.le(), operator.gte(), etc.
        out_field : str
            Field to create in self.objects to store result of adjacency test.

        Returns
        --------
        None : modifies self.objects in place
        """
        # For all rows where neighbor_values have been computed, compare
        # neighbor values to value_thresh using the given value_op. If any are
        # True, True is returned
        self.objects[out_field] = (self.objects[
                        ~self.objects[neb_values_fld].isnull()][neb_values_fld]
                        .apply(lambda x:
                               any(value_op(v, value_thresh)
                                   for v in x.values())))

#%%
obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch\region_grow_objs.shp'
# Existing column name
med_mean = 'MED_mean'
cur_mean = 'CurPr_mean'
ndvi_mean = 'NDVI_mean'
# Neighbor value column names
med_nv = 'nv_{}'.format(med_mean)
# Merge column names
merge_candidates = 'merge_candidates'
merge_path = 'merge_path'
mergeable = 'mergeable'
value_fields = [('MDFM_mean', 'mean'), ('MED_mean', 'mean'),
                ('CurPr_mean', 'mean'), ('NDVI_mean', 'mean'),
                ('EdgDen_mea', 'mean'), ('Slope_mean', 'mean'),
                ('CClass_majority', 'majority')]
merge_col = med_mean

ios = ImageObjects(objects_path=obj_p)
ios.compute_area()
# Get neighbor ids into a list in columns 'neighbors'
ios.get_neighbors()
ios.compute_neighbor_values(med_mean, med_nv)



# Pairwise functions
def within_range(a, b, range):
    return operator.le(abs(a - b), range)


def pairwise_match(row, possible_match, pairwise_criteria):
    """Tests each set of pairwise critieria against the current row
    and a possible match.
    Parameters
    ---------
    row : pd.Series
        Must contain all fields in pairwise criteria
    possible_match : pd.Series
        Must contain all fields in pairwise critieria
    pairwise_criteria : dict
        Dict of critiria, supported types:
            'within': {'field': "field_name", 'range': "within range"}
            'threshold: {'field': "field_name, 'op', operator comparison fxn,
                         'threshold': value to use in fxn}
    Returns
    -------
    bool : True is all criteria are met
    """
    criteria_met = []
    for criteria_type, params in pairwise_criteria.items():
        if criteria_type == 'within':
            criteria_met.append(within_range(row[params['field']],
                                             possible_match[params['field']],
                                             params['range']))
        elif criteria_type == 'threshold':
            criteria_met.append(
                params['op'](possible_match[params['field']],
                             params['threshold']))
    return all(criteria_met)


#%%
# Args
merge_field = med_mean
merge_nv_field = med_nv
# Criteria to determine candidates to be merged. This does not limit
# which objects they may be merge to, that is done with pairwise criteria.
merge_criteria = [(area_fld, operator.lt, 17.6),
                  (ndvi_mean, operator.lt, 0)]
# Criteria to check between a merge candidate and merge option
pairwise_criteria = {'within': {'field': cur_mean, 'range': 1},}
                     # 'threshold': {'field': ndvi_mean, 'op': operator.lt,
                     #               'threshold': 0}}

ios.pseudo_merging(merge_field=med_mean, merge_criteria=merge_criteria,
                   pairwise_criteria=pairwise_criteria)

#%%
write_gdf(ios.objects.reset_index(), r'E:\disbr007\umn\2020sep27_eureka\scratch\region_grow_objs_idx_2.shp',
          to_str_cols=[nebs_fld, med_nv, merge_path])


#%% object with value within distance
obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch\region_grow_objs.shp'
obj = gpd.read_file(obj_p)
field = 'CurPr_mean'
candidate_value = 25
dist_to_value = -25
dist = 2

selected = obj[obj[field] > candidate_value]

for i, r in selected.iterrows():
    if i == 348:
        tgdf = gpd.GeoDataFrame([r], crs=obj.crs)
        within_area = gpd.GeoDataFrame(geometry=tgdf.buffer(dist), crs=obj.crs)
        # overlay
        # look up values for features in overlay matches
        # if meet dist to value, True
