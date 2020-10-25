# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt

import pandas as pd

from misc_utils.logging_utils import create_logger
from obia_utils.ImageObjects import ImageObjects


pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'INFO')

plt.style.use('pycharm')

#%%
obj_p = r'E:\disbr007\umn\2020sep27_eureka\scratch\rgo.shp'
# Existing column name
med_mean = 'MED_mean'
cur_mean = 'CurPr_mean'
ndvi_mean = 'NDVI_mean'
slope_mean = 'Slope_mean'
# Neighbor value column names
med_nv = 'nv_{}'.format(med_mean)
ndvi_nv = 'nv_{}'.format(ndvi_mean)
# Merge column names
merge_candidates = 'merge_candidates'
merge_path = 'merge_path'
mergeable = 'mergeable'
value_fields = [('MDFM_mean', 'mean'), ('MED_mean', 'mean'),
                ('CurPr_mean', 'mean'), ('NDVI_mean', 'mean'),
                ('EdgDen_mea', 'mean'), ('Slope_mean', 'mean'),
                ('CClass_maj', 'majority')
                ]
merge_col = med_mean

#%%
ios = ImageObjects(objects_path=obj_p, value_fields=value_fields)
#%%
# Args
merge_field = med_mean
# Criteria to determine candidates to be merged. This does not limit
# which objects they may be merge to, that is done with pairwise criteria.
merge_criteria = [
                  # (ios.area_fld, operator.lt, 1500),
                  (ndvi_mean, operator.lt, 0),
                  (med_mean, operator.lt, 0.3),
                  (slope_mean, operator.gt, 2)
                 ]
# Criteria to check between a merge candidate and merge option
pairwise_criteria = {
    # 'within': {'field': cur_mean, 'range': 10},
    'threshold': {'field': ndvi_mean, 'op': operator.lt, 'threshold': 0}
}
#%%
ios.compute_area()
# Get neighbor ids into a list in columns 'neighbors'
ios.get_neighbors()
ios.compute_neighbor_values(merge_field)

#%%
# Determines merge paths
ios.pseudo_merging(merge_field=med_mean, merge_criteria=merge_criteria,
                   pairwise_criteria=pairwise_criteria)
#%%
# Does merging
ios.merge()
#%%
logger.info('Writing...')
out_footprint = r'E:\disbr007\umn\2020sep27_eureka\scratch\rbo_merge_med.shp'
ios.write_objects(out_footprint)


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
