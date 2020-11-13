# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt

import pandas as pd
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import select_in_aoi
from obia_utils.ImageObjects import ImageObjects



pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'INFO')

plt.style.use('pycharm')


#%%
obj_p = r'E:\disbr007\umn\2020sep27_eureka\seg\grm_ms' \
        r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-' \
        r'500287602150_01_P009_u16mr3413_pansh_test_aoi_468_' \
        r'bst250x0ni0s0spec0x25spat25x0_cln.shp'
aoi_p = r'E:\disbr007\umn\2020sep27_eureka\aois\test_aoi_sub.shp'
aoi = gpd.read_file(aoi_p)

# Existing column name
med_mean = 'MED_mean'
cur_mean = 'CurPr_mean'
ndvi_mean = 'NDVI_mean'
slope_mean = 'Slope_mean'
mdfm_mean = 'MDFM_mean'
edged_mean = 'EdgDen_mea'
cclass_maj = 'CClass_maj'


#%%
value_fields = [(mdfm_mean, 'mean'), (med_mean, 'mean'),
                (cur_mean, 'mean'), (ndvi_mean, 'mean'),
                (edged_mean, 'mean'), (slope_mean, 'mean'),
                (cclass_maj, 'majority')
                ]

if aoi_p:
    logger.info('Subsetting objects to AOI...')
    gdf = select_in_aoi(gpd.read_file(obj_p), aoi, centroid=True)
    ios = ImageObjects(objects_path=gdf, value_fields=value_fields)
else:
    ios = ImageObjects(objects_path=obj_p, value_fields=value_fields)

#%% Merging parameters
# Merge column names
merge_candidates = 'merge_candidates'
merge_path = 'merge_path'
mergeable = 'mergeable'

#%%
# Args
# Criteria to determine candidates to be merged. This does not limit
# which objects they may be merge to, that is done with pairwise criteria.
merge_criteria = [
                  (ios.area_fld, operator.lt, 1000000),
                  (ndvi_mean, operator.lt, 0),
                  # (med_mean, operator.lt, 0.3),
                  # (slope_mean, operator.gt, 2)
                 ]
# Criteria to check between a merge candidate and merge option
pairwise_criteria = {
    # 'within': {'field': cur_mean, 'range': 10},
    'threshold': {'field': ndvi_mean, 'op': operator.lt, 'threshold': 0}
}
#%%
# Get neighbor ids into a list in column 'neighbors'
ios.get_neighbors()
#%%
ios.compute_area()
# ios.calc_object_stats()
ios.compute_neighbor_values(cur_mean)


#%% RULESET
# TODO: Revisit naming of adjacency fields
#%% High curvature adjacent to low curvature
high_curv = 25
low_curv = -25
curv_h_adj_l = 'curv_gt25_adj_lt25'
ios.adjacent_to(in_field=cur_mean, op=operator.lt, thresh=low_curv,
                src_field=cur_mean, src_op=operator.gt, src_thresh=high_curv,
                out_field=curv_h_adj_l)
#%% Adjacent to both high and low curvature
curv_adj_hl = 'adj_gt25_lt25'
ios.objects[curv_adj_hl] = (ios.adjacent_to(in_field=cur_mean, op=operator.lt,
                                            thresh=low_curv) &
                            (ios.adjacent_to(in_field=cur_mean, op=operator.gt,
                                             thresh=high_curv)))
#%% NDVI less than 0 adjacent greater than 0
ndvi_lt0_adj_gt0 = 'ndvi_lt0_adj_gt0'
ndvi_adj = ios.adjacent_to(in_field=ndvi_mean, op=operator.gt, thresh=0,
                           src_field=ndvi_mean, src_op=operator.lt, src_thresh=0,
                           out_field=ndvi_lt0_adj_gt0)
#%% NDVI adjacent to less than 0 and greater than 0
ndvi_adj_gt0_lt0 = 'adj_ndvi_lt0_gt0'
ios.objects[ndvi_adj_gt0_lt0] = (ios.adjacent_to(in_field=ndvi_mean, op=operator.lt,
                                            thresh=0) &
                            (ios.adjacent_to(in_field=ndvi_mean, op=operator.gt,
                                             thresh=0)))
#%%
# Determines merge paths
# ios.pseudo_merging(merge_fields=[med_mean, ndvi_mean],
#                    merge_criteria=merge_criteria,
#                    pairwise_criteria=pairwise_criteria)
#%%
# Does merging
# ios.merge()
#%%
logger.info('Writing...')
out_footprint = r'E:\disbr007\umn\2020sep27_eureka\scratch\adj_obj_bool.geojson'
ios.write_objects(out_footprint, overwrite=True)


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

#%% Plotting
fig, ax = plt.subplots(1, 1)
ios.objects.plot(ax=ax)
fig.show()
