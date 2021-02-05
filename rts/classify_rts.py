# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt
import numpy as np
import sys

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import select_in_aoi, dissolve_touching
from obia_utils.ImageObjects import ImageObjects, create_rule, overlay_any_objects
from archive_analysis.archive_analysis_utils import grid_aoi

pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'DEBUG')

# %% Fields
# Existing fields
med_mean = 'med_mean'
cur_mean = 'curv_mean'
ndvi_mean = 'ndvi_mean'
slope_mean = 'slope_mean'
rug_mean = 'ruggedness'
sa_rat_mean = 'sar_mean'
elev_mean = 'dem_mean'
img_mean = 'img_mean'
delev_mean = 'diff_mean'

value_fields = [
    (med_mean, 'mean'),
    (cur_mean, 'mean'),
    (ndvi_mean, 'mean'),
    (slope_mean, 'mean'),
    (rug_mean, 'mean'),
    (sa_rat_mean, 'mean'),
    (elev_mean, 'mean'),
    (delev_mean, 'mean'),
]

# Created columns
# simple_thresholds = 'hw_simple_thresholds'
# adj_rules = 'adj_rules'
hw_candidate = 'headwall_candidate'
grow_candidate = 'grow_candidate'
grow_object = 'grow_object'

# rts_simple_thresholds = 'rts_simple_threshold'
contains_hw = 'contains_hw'
intersects_rts_cand = 'inters_rts'
rts_candidate = 'rts_candidate'
rts_cand_bool = 'rts_cand'

# truth = 'truth'
threshold_rule = 'threshold'
adjacent_rule = 'adjacent'

# Columns to be converted to strings before writing
to_str_cols = []


def classify_rts(sub_objects_path,
                 super_objects_path,
                 headwall_candidates_out=None,
                 headwall_candidates_centroid_out=None,
                 rts_predis_out=None,
                 rts_candidates_out=None,
                 aoi_path=None,
                 headwall_candidates_in=None,
                 aoi=None):
    logger.info('Classifying RTS...')

    #%% RULESET
    # Headwall Rules
    # Ruggedness
    r_ruggedness = create_rule(rule_type=threshold_rule,
                               in_field=rug_mean,
                               op=operator.gt,
                               threshold=0.2,
                               out_field=True)
    # Surface Area Ratio
    r_saratio = create_rule(rule_type=threshold_rule,
                            in_field=sa_rat_mean,
                            op=operator.gt,
                            threshold=1.01,
                            out_field=True)
    # Slope
    r_slope = create_rule(rule_type=threshold_rule,
                          in_field=slope_mean,
                          op=operator.gt,
                          threshold=8,
                          out_field=True)
    # NDVI
    r_ndvi = create_rule(rule_type=threshold_rule,
                         in_field=ndvi_mean,
                         op=operator.lt,
                         threshold=0,
                         out_field=True)
    # MED
    r_med = create_rule(rule_type=threshold_rule,
                        in_field=med_mean,
                        op=operator.lt,
                        threshold=0,
                        out_field=True)
    # Curvature (high)
    r_curve = create_rule(rule_type=threshold_rule,
                          in_field=cur_mean,
                          op=operator.gt,
                          threshold=2.5,
                          out_field=True)
    # Difference in DEMs
    r_delev = create_rule(rule_type=threshold_rule,
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
                           r_curve,
                           r_delev]

    # Adjacency rules
    # Adjacent Curvature
    r_adj_high_curv = create_rule(rule_type=adjacent_rule,
                                  in_field=cur_mean,
                                  op=operator.gt,
                                  threshold=30,
                                  out_field=True)
    r_adj_low_curv = create_rule(rule_type=adjacent_rule,
                                 in_field=cur_mean,
                                 op=operator.lt,
                                 threshold=-30,
                                 out_field=True)
    # Adjacent MED
    # TODO: Change to adjacent to or IS low MED?
    r_adj_low_med = create_rule(rule_type=adjacent_rule,
                                in_field=med_mean,
                                op=operator.lt,
                                threshold=-0.2,
                                out_field=True)
    # All adjacent rules
    r_adj_rules = [r_adj_low_curv, r_adj_high_curv, r_adj_low_med]


    #%% RTS Rules
    r_rts_ndvi = create_rule(rule_type=threshold_rule,
                             in_field=ndvi_mean,
                             op=operator.lt,
                             threshold=0,
                             out_field=True)

    r_rts_med = create_rule(rule_type=threshold_rule,
                            in_field=med_mean,
                            op=operator.lt,
                            threshold=0,
                            out_field=True)

    r_rts_slope = create_rule(rule_type=threshold_rule,
                              in_field=slope_mean,
                              op=operator.gt,
                              threshold=3,
                              out_field=True)

    r_rts_delev = create_rule(rule_type=threshold_rule,
                              in_field=delev_mean,
                              op=operator.lt,
                              threshold=-0.5,
                              out_field=True)

    r_rts_conhw = create_rule(rule_type=threshold_rule,
                              in_field=contains_hw,
                              op=operator.eq,
                              threshold=True,
                              out_field=True)

    r_rts_simple_thresholds = [r_rts_ndvi,
                               r_rts_med,
                               r_rts_slope,
                               r_rts_delev,
                               r_rts_conhw]


    #%% HEADWALL CANDIDATES
    #%% Load candidate headwall objects
    if not headwall_candidates_in:
        logger.info('Loading headwall candidate objects...')
        if aoi_path:
            aoi = gpd.read_file(aoi_path)
            logger.info('Subsetting objects to AOI...')
            gdf = select_in_aoi(gpd.read_file(sub_objects_path), aoi, centroid=True)
            hwc = ImageObjects(objects_path=gdf, value_fields=value_fields)
        else:
            hwc = ImageObjects(objects_path=sub_objects_path, value_fields=value_fields)


        #%% Classify headwalls
        logger.info('Determining headwall candidates...')
        hwc.classify_objects(hw_candidate,
                             threshold_rules=r_simple_thresholds,
                             adj_rules=r_adj_rules)
        logger.info('Headwall candidates found: {:,}'.format(
            len(hwc.objects[hwc.objects[hwc.class_fld] == hw_candidate])))

        #%% Write headwall candidates
        logger.info('Writing headwall candidates...')
        hwc.write_objects(headwall_candidates_out,
                          to_str_cols=to_str_cols,
                          overwrite=True)
        if headwall_candidates_centroid_out:
            hwc_centroid = ImageObjects(
                copy.deepcopy(
                    hwc.objects.set_geometry(hwc.objects.geometry.centroid)))
            hwc_centroid.write_objects(headwall_candidates_centroid_out,
                                       overwrite=True)
    else:
        hwc = ImageObjects(objects_path=headwall_candidates_in,
                           value_fields=value_fields)

    #%% RETROGRESSIVE THAW SLUMPS
    #%% Load super objects
    logger.info('Loading RTS candidate objects...')
    so = ImageObjects(super_objects_path,
                      value_fields=value_fields)
    logger.info('Determining RTS candidates...')

    #%% Find objects that contain headwalls of a higher elevation than
    # themselves
    so.objects[contains_hw] = so.objects.apply(
        lambda x: overlay_any_objects(
            x.geometry,
            hwc.objects[hwc.objects[hwc.class_fld] == hw_candidate],
            predicate='contains',
            threshold=x[elev_mean],
            other_value_field=elev_mean,
            op=operator.gt),
        axis=1)

    #%% Classify
    so.classify_objects(class_name=rts_candidate,
                        threshold_rules=r_rts_simple_thresholds)
    # # Add bool field for RTS candidate or not
    # so.objects[rts_cand_bool] = np.where(so.objects[so.class_fld] == rts_candidate,
    #                                   1,
    #                                   0)

    logger.info('RTS candidates found: {}'.format(
        len(so.objects[so.objects[so.class_fld] == rts_candidate])))

    if rts_predis_out:
        # Write classified objects before growing
        so.write_objects(rts_predis_out,
                         to_str_cols=to_str_cols,
                         overwrite=True)

    #%% Dissolve touching candidates
    rts_dissolved = dissolve_touching(so.objects[so.objects[so.class_fld]
                                                 == rts_candidate],
                                      aggfunc='mean')
    so.objects = pd.concat([so.objects[so.objects[so.class_fld]
                                       != rts_candidate],
                            rts_dissolved])

    #%% Write RTS candidates
    logger.info('Writing RTS candidates...')
    so.write_objects(rts_candidates_out,
                     to_str_cols=to_str_cols,
                     overwrite=True)

    return rts_candidates_out


def grow_rts_candidates(candidates: ImageObjects,
                        subobjects: ImageObjects):
    # in_rts = 'on_border'
    # Locate border touching objects
    # subobjects.objects[on_border] = subobjects.objects.index.isin(
    #     gpd.sjoin(subobjects.objects.set_geometry(subobjects.objects.geometry.centroid),
    #               candidates.objects[candidates.objects[candidates.class_fld] == rts_candidate]
    #               .set_geometry(candidates.objects.geometry.boundary),
    #               how='inner').index)

    # Locate objects with centroid within rts_candidates
    logger.info('Locating merge seeds within RTS candidates...')
    in_rts = 'in_rts'
    subobjects.objects[in_rts] = subobjects.objects.index.isin(
        gpd.overlay(subobjects.objects.reset_index()
                    .set_geometry(subobjects.objects.centroid),
                    candidates.objects[candidates.objects[candidates.class_fld]
                                       == rts_candidate]).set_index('index_1')
        .index)

    # Add on_border field to value fields
    # subobjects.value_fields[on_border] = 'bool_or'
    subobjects.value_fields[in_rts] = 'bool_or'

    # Determine merge paths
    # Merge seeds
    in_rts_rule = create_rule(rule_type=threshold_rule,
                              in_field=in_rts,
                              op=operator.eq,
                              threshold=True,
                              out_field=True)
    delev_rule = create_rule(rule_type=threshold_rule,
                             in_field=delev_mean,
                             op=operator.lt,
                             threshold=-0.5,
                             out_field=True)
    ndvi_rule = create_rule(rule_type=threshold_rule,
                            in_field=ndvi_mean,
                            op=operator.lt,
                            threshold=-0.01,
                            out_field=True)
    img_rule = create_rule(rule_type=threshold_rule,
                           in_field=img_mean,
                           op=operator.lt,
                           threshold=1200,
                           out_field=True)
    med_rule = create_rule(rule_type=threshold_rule,
                           in_field=med_mean,
                           op=operator.lt,
                           threshold=1,
                           out_field=True)
    slope_rule = create_rule(rule_type=threshold_rule,
                             in_field=slope_mean,
                             op=operator.gt,
                             threshold=5,
                             out_field=True)

    subobjects.merge_seeds([in_rts_rule,
                            delev_rule,
                            ndvi_rule,
                            img_rule,
                            med_rule,
                            slope_rule])

    # Merge candidate rules
    mc_fot = [(in_rts, operator.eq, True),
              (delev_mean, operator.lt, -0.5),  # -0.5
              (ndvi_mean, operator.lt, -0.01),  # -0.01
              (img_mean, operator.lt, 1200),  # 1200
              (med_mean, operator.lt, 1),  # 1
              (slope_mean, operator.gt, 5)]  # 5

    # Pairwise rules
    # Greater slope than self
    slope_pwr = {'threshold': {'field': slope_mean,
                               'op': operator.gt,
                                'threshold': 'self'}}

    img_pwr = {'threshold': {'field': img_mean,
                             'op': operator.lt,
                             'threshold': 'self'}}
    ndvi_pwr = {'threshold': {'field': ndvi_mean,
                              'op': operator.lt,
                              'threshold': 'self'}}
    pc = [img_pwr, ndvi_pwr]
    # pc = None

    gf = [slope_mean, delev_mean, img_mean]
    max_iter = 100

    subobjects.pseudo_merging(mc_fields_ops_thresholds=mc_fot,
                              pairwise_criteria=pc,
                              grow_fields=gf,
                              max_iter=max_iter,
                              merge_seeds=True)

    # Merge
    subobjects.merge()

    return subobjects

