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
from misc_utils.gpd_utils import select_in_aoi, explode_multi
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
    """Determines if any others are in geometry, optionally using the
    centroids of others, optionally using a threshold on others to
    reduce the number of others that are considered"""
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


def classify_rts(sub_objects_path,
                 super_objects_path,
                 headwall_candidates_out=None,
                 headwall_candidates_centroid_out=None,
                 rts_pregrow_out=None,
                 rts_candidates_out=None,
                 aoi_path=None,
                 headwall_candidates_in=None):
    logger.info('Classifying RTS...')
    #%% Fields
    # Existing fields
    med_mean = 'med_mean'
    cur_mean = 'curv_mean'
    ndvi_mean = 'ndvi_mean'
    slope_mean = 'slope_mean'
    rug_mean = 'ruggedness'
    sa_rat_mean = 'sar_mean'
    elev_mean = 'dem_mean'
    pan_mean = 'img_mean'
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

    # truth = 'truth'
    threshold_rule = 'threshold'
    adjacent_rule = 'adjacent'

    # Columns to be converted to strings before writing
    to_str_cols = []

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
                              op=operator.gt,
                              threshold=-0.5)
    r_rts_conhw = create_rule(rule_type=threshold_rule,
                              in_field=contains_hw,
                              op=operator.eq,
                              threshold=True)

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
        lambda x: contains_any_objects(
            x.geometry,
            hwc.objects[hwc.objects[hwc.class_fld] == hw_candidate],
            threshold=x[elev_mean],
            other_value_field=elev_mean,
            op=operator.gt),
        axis=1)

    #%% Classify
    so.classify_objects(class_name=rts_candidate,
                        threshold_rules=r_rts_simple_thresholds)

    logger.info('RTS candidates found: {}'.format(
        len(so.objects[so.objects[so.class_fld] == rts_candidate])))

    if rts_pregrow_out:
        # Write classified objects before growing
        so.write_objects(rts_pregrow_out,
                         to_str_cols=to_str_cols,
                         overwrite=True)

    #%% Grow RTS objects into subobjects
    logger.info('Growing RTS features...')
    """
    diff_mean < -0.7
    ndvi_mean < 0
    med_mean < 1
    img_mean < 1100
    """
    # Select subobjects that meet thresholds
    r_g_delev = create_rule(rule_type=threshold_rule,
                            in_field=delev_mean,
                            op=operator.lt,
                            threshold=-0.7)
    r_g_ndvi = create_rule(rule_type=threshold_rule,
                           in_field=ndvi_mean,
                           op=operator.lt,
                           threshold=1)
    r_g_med = create_rule(rule_type=threshold_rule,
                          in_field=med_mean,
                          op=operator.lt,
                          threshold=1)
    r_g_img = create_rule(rule_type=threshold_rule,
                          in_field=pan_mean,
                          op=operator.lt,
                          threshold=1100)

    r_grow_rules = [r_g_delev, r_g_ndvi, r_g_med, r_g_img]

    hwc.classify_objects(grow_candidate,
                         threshold_rules=r_grow_rules)

    # Subset to subobjects that intersect with class = 'rts_candidate'
    hwc.objects[intersects_rts_cand] = hwc.objects.index.isin(
        gpd.sjoin(hwc.objects[hwc.objects[hwc.class_fld] == grow_candidate],
                  so.objects[so.objects[so.class_fld] == rts_candidate],
                  how='inner').index
    )

    r_g_inter_rts = create_rule(rule_type=threshold_rule,
                                in_field=intersects_rts_cand,
                                op=operator.eq,
                                threshold=True)

    hwc.classify_objects(grow_object,
                         threshold_rules=[r_g_inter_rts],
                         overwrite_class=True)

    # Add grow objects selection to superobjects
    so.objects = pd.concat([so.objects,
                           hwc.objects.loc[hwc.objects[hwc.class_fld] == grow_object]])

    # Dissolve selection into superobjects
    # so.objects[so.objects[so.class_fld] == grow_candidate][so.class_fld] = rts_candidate
    # dissolved = so.objects.dissolve(by='class')
    # dissolved = explode_multi(dissolved)
    # so.objects = dissolved.reset_index()

    #%% Clean up objects
    # Remove holes

    #%% Write RTS candidates
    logger.info('Writing headwall candidates...')
    so.write_objects(rts_candidates_out,
                     to_str_cols=to_str_cols,
                     overwrite=True)

    return rts_candidates_out
