# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import select_in_aoi
from obia_utils.ImageObjects import ImageObjects


pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'DEBUG')


#%%
def rule_field_name(rule):
    fn = '{}_{}{}'.format(rule['in_field'],
                           str(rule['op'])[-3:-1],
                           str(rule['threshold']).replace('.', 'x'))
    if rule['rule_type'] == 'adjacent':
        fn = '{}_{}'.format('adj', fn)
    return fn


def create_rule(rule_type, in_field, op, threshold, out_field=None, **kwargs):
    rule = {'rule_type': rule_type,
            'in_field': in_field,
            'op': op,
            'threshold': threshold}

    if out_field is True:
        rule['out_field'] = rule_field_name(rule)

    return rule


def contains_any_objects(geometry, others, centroid=True,
                         threshold=None,
                         other_value_field=None,
                         op=None):
    # logger.debug('Finding features that contain others...')
    if threshold:
        # Subset others to only include those that meet threshold provided
        others = others[op(others[other_value_field], threshold)]

    # Determine if object contains others
    if centroid:
        others_geoms = others.geometry.centroid.values
    else:
        others_geoms = others.geometry.values
    contains = np.any([geometry.contains(og) for og in others_geoms])

    return contains


#%% In and out paths
super_obj_p = r'E:\disbr007\umn\2020sep27_eureka\seg\grm' \
              r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-' \
              r'M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi_468_' \
              r'bst250x0ni0s0spec0x5spat25x0_cln_zs.shp'
# super_obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch_2020nov30\so.shp'
hw_obj_p = r'E:\disbr007\umn\2020sep27_eureka\seg\hw_seg' \
        r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-' \
        r'M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi_' \
        r'bst100x0ni100s0spec0x3spat50x0_cln_zs.shp'
# hw_obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch_2020nov30\sbo.shp'

hw_candidates_p = r'E:\disbr007\umn\2020sep27_eureka\scratch_2020nov30' \
                  r'\hw_candidates.geosjon'

rts_candidates_p = r'E:\disbr007\umn\2020sep27_eureka\scratch_2020nov30' \
                  r'\rts_candidates4.geojson'

aoi_p = r'E:\disbr007\umn\2020sep27_eureka\aois\test_aoi_sub.shp'
aoi_p = None
#%% Fields
# Existing fields
med_mean = 'MED_mean'
cur_mean = 'CurPr_mean'
ndvi_mean = 'NDVI_mean'
slope_mean = 'Slope_mean'
rug_mean = 'RugIn_mean'
sa_rat_mean = 'SAratio_me'
elev_mean = 'elev_mean'
delev_mean = 'dDEM_mean'
dndvi_mean = 'dNDVI_mean'
# mdfm_mean = 'MDFM_mean'
# edged_mean = 'EdgDen_mea'
# cclass_maj = 'CClass_maj'

value_fields = [
    (med_mean, 'mean'),
    (cur_mean, 'mean'),
    (ndvi_mean, 'mean'),
    (slope_mean, 'mean'),
    (rug_mean, 'mean'),
    (sa_rat_mean, 'mean'),
    (elev_mean, 'mean')
    # (mdfm_mean, 'mean'),
    # (edged_mean, 'mean'),
    # (cclass_maj, 'majority')
    ]

# Created columns

simple_thresholds = 'hw_simple_thresholds'
adj_rules = 'adj_rules'
hw_candidate = 'headwall_candidate'

rts_simple_thresholds = 'rts_simple_threshold'
contains_hw = 'contains_hw'
rts_candidate = 'rts_candidate'
truth = 'truth'

# Columns to be converted to strings before writing
to_str_cols = []

#%% RULESET
# Headwall Rules
# Ruggedness
r_ruggedness = create_rule(rule_type='threshold',
                           in_field=rug_mean,
                           op=operator.gt,
                           threshold=0.25,
                           out_field=True)
# Surface Area Ratio
r_saratio = create_rule(rule_type='threshold',
                        in_field=sa_rat_mean,
                        op=operator.gt,
                        threshold=1.01,
                        out_field=True)
# Slope
r_slope = create_rule(rule_type='threshold',
                      in_field=slope_mean,
                      op=operator.gt,
                      threshold=8,
                      out_field=True)
# NDVI
r_ndvi = create_rule(rule_type='threshold',
                     in_field=ndvi_mean,
                     op=operator.lt,
                     threshold=0,
                     out_field=True)
# MED
r_med = create_rule(rule_type='threshold',
                    in_field=med_mean,
                    op=operator.lt,
                    threshold=0,
                    out_field=True)
# Difference in DEMs
r_delev = create_rule(rule_type='threshold',
                      in_field=delev_mean,
                      op=operator.lt,
                      threshold=-0.5,
                      out_field=True)

# All simple threshold rules
r_simple_thresholds = [r_ruggedness,
                       r_saratio,
                       r_slope,
                       r_ndvi,
                       r_med,
                       r_delev]

# Adjacency rules
# Adjacent Curvature
r_adj_high_curv = create_rule(rule_type='adjacent',
                              in_field=cur_mean,
                              op=operator.gt,
                              threshold=30,
                              out_field=True)
r_adj_low_curv = create_rule(rule_type='adjacent',
                             in_field=cur_mean,
                             op=operator.lt,
                             threshold=-30,
                             out_field=True)
# Adjacent MED
r_adj_low_med = create_rule(rule_type='adjacent',
                            in_field=med_mean,
                            op=operator.lt,
                            threshold=-0.2,
                            out_field=True)
# All adjacent rules
r_adj_rules = [r_adj_low_curv, r_adj_high_curv, r_adj_low_med]

#%% Load candidate headwall objects
logger.info('Loading headwall candidate objects...')
if aoi_p:
    aoi = gpd.read_file(aoi_p)
    logger.info('Subsetting objects to AOI...')
    gdf = select_in_aoi(gpd.read_file(hw_obj_p), aoi, centroid=True)
    hwc = ImageObjects(objects_path=gdf, value_fields=value_fields)
else:
    hwc = ImageObjects(objects_path=hw_obj_p, value_fields=value_fields)

#%% Subset by simple thresholds first
logger.info('Determining headwall candidates...')
hwc.apply_rules(r_simple_thresholds, out_field=simple_thresholds)

#%% Get neighbors for those objects that meet thresholds
hwc.get_neighbors(subset=hwc.objects[hwc.objects[simple_thresholds]])

#%%
hwc.compute_area()
# hwc.calc_object_stats()
hwc.compute_neighbor_values(cur_mean)
hwc.compute_neighbor_values(med_mean)

#%% Adjacency rules
hwc.apply_rules(r_adj_rules, out_field=adj_rules)
#%% Adjacent to both high and low curvature
# high_curv = 40
# low_curv = -30
# curv_adj_hl = 'adj{}_gt{}_lt{}'.format(cur_mean, high_curv, low_curv)
# hwc.objects[curv_adj_hl] = (hwc.adjacent_to(in_field=cur_mean, op=operator.lt,
#                                             threshold=low_curv) &
#                             (hwc.adjacent_to(in_field=cur_mean, op=operator.gt,
#                                              threshold=high_curv)))
# best_low_curv = 'b_low_curv'
# best_high_curv = 'b_high_curv'
# hwc.objects[best_low_curv] = hwc.best_adjacent_to(in_field=cur_mean,
#                                                  op=operator.lt)
# hwc.objects[best_high_curv] = hwc.best_adjacent_to(in_field=cur_mean,
#                                                   op=operator.gt)
# to_str_cols.extend([best_low_curv, best_high_curv])

#%% Adjacent to low MED
# adj_low_med = -0.2
# med_adj_l = 'adj{}_lt{}'.format(med_mean, adj_low_med)
# hwc.objects[med_adj_l] = hwc.adjacent_to(med_mean, op=operator.lt,
#                                          threshold=adj_low_med)
# best_low_med = 'b_low_med'
# hwc.objects[best_low_med] = hwc.best_adjacent_to(in_field=med_mean,
#                                                  op=operator.lt)
# to_str_cols.append(best_low_med)

#%% All headwall criteria
hw_criteria = [simple_thresholds,
               adj_rules]
hwc.objects[hw_candidate] = hwc.objects.apply(
    lambda x: np.all([x[c] for c in hw_criteria]), axis=1)

#%%
# logger.info('Writing headwall candidates...')
# hwc.write_objects(hw_candidates_p,
#                   to_str_cols=to_str_cols,
#                   overwrite=True)

#%% Find RTS
#%% RTS Rules
r_rts_ndvi = create_rule(rule_type='threshold',
                         in_field=ndvi_mean,
                         op=operator.lt,
                         threshold=0,
                         out_field=True)
r_rts_med = create_rule(rule_type='threshold',
                        in_field=med_mean,
                        op=operator.lt,
                        threshold=0,
                        out_field=True)
r_rts_slope = create_rule(rule_type='threshold',
                          in_field=slope_mean,
                          op=operator.gt,
                          threshold=3,
                          out_field=True)
r_rts_delev = create_rule(rule_type='threshold',
                          in_field=delev_mean,
                          op=operator.gt,
                          threshold=-0.5)
r_rts_simple_thresholds = [r_rts_ndvi,
                           r_rts_med,
                           r_rts_slope]

#%% Load super objects
logger.info('Loading RTS candidate objects...')
so = ImageObjects(super_obj_p,
                  value_fields=value_fields)
#%%
logger.info('Determining RTS candidates...')
# Find objects that meet thresholds
so.apply_rules(r_rts_simple_thresholds, out_field=rts_simple_thresholds)


#%% Find objects that contain potential headwalls of a high elevation
so.objects[contains_hw] = so.objects.apply(
    lambda x: contains_any_objects(x.geometry,
                                   hwc.objects[hwc.objects[hw_candidate]],
                                   threshold=x[elev_mean],
                                   other_value_field=elev_mean,
                                   op=operator.gt), axis=1)

# so.objects[contains_hw] = so.objects.geometry.apply(
#     lambda x: np.any([x.contains(hw_p) for hw_p in
#                       hwc.objects[hwc.objects[hw_candidate]].centroid.values]))

#%% Determine if all criteria met
rts_criteria = [contains_hw,
                rts_simple_thresholds]

so.objects[rts_candidate] = so.objects.apply(
    lambda x: np.all([x[c] for c in rts_criteria]), axis=1)
logger.info('RTS candidates found: '
            '{}'.format(len(so.objects[so.objects[rts_candidate]])))
#%% Write RTS candidates
# logger.info('Writing headwall candidates...')
# so.write_objects(rts_candidates_p.replace('es.', 'es2.'),
#                  to_str_cols=to_str_cols,
#                  overwrite=True)
#%%
logger.info('Growing candidates objects...')
# Find neighbors for objects that contain headwall candidate
so.get_neighbors(so.objects[so.objects[contains_hw]==True])


#%% Get values for fields that growing is based on
so.compute_neighbor_values(value_field=delev_mean)


#%% Rules for growing
# Candidates to grow into
r_grow_delev = (delev_mean, operator.lt, 0)  # difference in DEMs < 0
# TODO: Make this criteria for starting point, not requirement to be merged.
#  When growing, must pass 'contains' to merged object (or recompute but
#  that'd be slower).
r_grow_contains_hw = (contains_hw, operator.eq, True)  # must contain hw
# TODO: Add rules:
#  1. grow into closest elev
#  2. grow into closest NDVI
#  3. grow closest pan


fields_ops_thresholds = [r_grow_delev,
                         r_grow_contains_hw]

# Determines merge paths
so.pseudo_merging(fields_ops_thresholds=fields_ops_thresholds,
                  pairwise_criteria=None)
#%%
# Does merging
so.merge()
so.write_objects(super_obj_p.replace('.shp', 'merged.shp'))

#%% object with value within distance
# obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch\region_grow_objs.shp'
# obj = gpd.read_file(obj_p)
# field = 'CurPr_mean'
# candidate_value = 25
# dist_to_value = -25
# dist = 2
#
# selected = obj[obj[field] > candidate_value]
#
# for i, r in selected.iterrows():
#     if i == 348:
#         tgdf = gpd.GeoDataFrame([r], crs=obj.crs)
#         within_area = gpd.GeoDataFrame(geometry=tgdf.buffer(dist), crs=obj.crs)
#         # overlay
#         # look up values for features in overlay matches
#         # if meet dist to value, True

