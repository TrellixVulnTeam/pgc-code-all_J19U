# -*- coding: utf-8 -*-
"""
Created on Thu May 14 12:19:21 2020

@author: disbr007
"""
import copy
import operator
import matplotlib.pyplot as plt

import pandas as pd
# from pandas.api.types import is_numeric_dtype
import geopandas as gpd
from shapely.geometry import Polygon

from misc_utils.logging_utils import create_logger
# from obia_utils.neighbors import subset_df, adj_neighbor
from obia_utils.ImageObjects import ImageObjects
from obia_utils.object_plotting import plot_objects

pd.options.mode.chained_assignment = None

logger = create_logger(__name__, 'sh', 'DEBUG')

plt.style.use('pycharm')

ms_img = r'E:\disbr007\umn\2020sep27_eureka\img' \
         r'\ortho_WV02_20140703_test_aoi' \
         r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-' \
         r'M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi.tif'
ndvi = r'E:\disbr007\umn\2020sep27_eureka\img\ndvi_WV02_20140703' \
       r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-500287602150_01_P009_u16mr3413_ndvi.tif'

obj_path = r'E:\disbr007\umn\2020sep27_eureka\seg' \
           r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-M1BS-500287602150_01_P009_u16mr3413_pansh_' \
           r'test_aoi_sr6_rr200x0_ms750_tx500_ty500.shp'

o = ImageObjects(obj_path)
# o.compute_neighbor_values('meanB0', 'neb_meanB0', subset=o.objects.loc[[i for i in range(0, 15)]])
# o.compute_area()
# o.merge_adj(area_fld, operator.gt, 26.2,
#             merge_on_fld='meanB0', merge_thresh=250, recompute_area=True)

# o.objects = o.objects.loc[[2, 3, 4]]

# img_kwargs = {'cmap': 'RdYlGn', 'vmin': -0.25, 'vmax': 0.25}
plot_objects(obj=o.objects, img=ms_img, rgb=[7,5,4], obj_extent=False)












# #%%
# # Paths
# tks_path = r'V:\pgc\data\scratch\jeff\ms\2020may12\tks_loc\lewk_2019_hs_selected_3413.shp'
# # seg_path = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_tpi31_tpi81_tpi101_stk_a6g_sr5_rr0x35_ms100_tx500_ty500_stats_wbt.shp'
# # seg_path = r'V:\pgc\data\scratch\jeff\ms\2020feb01\aoi6\seg\WV02_20150906_pcatdmx_slope_a6g_sr5_rr1_0_ms400_tx500_ty500_stats_nbs_wbt.shp'
# seg_path = r'V:\pgc\data\scratch\jeff\ms\2020may12\seg\grm\WV02_20140818_pca_MDFM_bst10x0ni30s0spec1x0spat0x5.shp'
# img_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\dems\pca\max_diff_from_mean\WV02_20140818_pca_MDFM.tif'
#
# # Existing columns
# unique_id = 'label'
# tpi31_mean = 'tpi31_mean'
# slope_mean = 'slope_mean'
#
# # %% Load segmentation
# logger.debug('Reading in segmentation...')
# seg = gpd.read_file(seg_path)
#
# # %% Reduce to just area around selected tks points
# tks = gpd.read_file(tks_path)
# if seg.crs != tks.crs:
#     tks = tks.to_crs(seg.crs)
# tks.geometry = tks.buffer(200)
#
# bminx, bminy, bmaxx, bmaxy = tks.total_bounds
# border_points = [(bminx, bminy), (bminx, bmaxy), (bmaxx, bmaxy), (bmaxx, bminy)]
#
# border = gpd.GeoDataFrame(geometry=[Polygon(border_points)])
# seg = gpd.overlay(seg, border)
# seg = seg.drop_duplicates(subset='label')
#
# # %% Plot objects on image
# plot_objects(obj=seg, img=img_p, band=0, obj_extent=True)
#
# # %%
# # Remove extra columns for testing
# seg = seg[[unique_id, tpi31_mean, slope_mean, 'geometry']]
#
# # Set index
# seg.set_index(unique_id, inplace=True)
# logger.debug('DataFrame has unique index: {}'.format(str(seg.index.is_unique)))
#
# # %%
#
#
# #%% Params
#
# hw_params = [('slope_mean',  '>', 6.5)]
#
# hw = subset_df(seg, params=hw_params)
#
# vc = 'MDEC_media'
# plt.style.use('spy4_blank')
# fig, ax = plt.subplots(1,1)
#
# plt.tight_layout(pad=3)
