# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 11:35:49 2020

@author: disbr007
"""
import argparse
import copy
import datetime
import numpy as np
import os
from pathlib import Path
import platform

import geopandas as gpd
import pandas as pd
from tqdm import tqdm

from dem_utils.dem_selector import dem_selector
# from dem_selector import dem_selector
from dem_utils.dem_utils import (dems2aoi_ovlp, dems2dems_ovlp,
                                 get_matchtag_path, combined_density,
                                 get_dem_path, get_filepath_field,
                                 nunatak2windows)
# from dem_utils import (dems2aoi_ovlp, dems2dems_ovlp,
#                        get_matchtag_path, combined_density,
#                        get_dem_path, get_filepath_field)
from misc_utils.raster_clip import clip_rasters
from misc_utils.logging_utils import create_logger
from misc_utils.gpd_utils import remove_unused_geometries, write_gdf

logger = create_logger(__name__, 'sh', 'DEBUG')
sub_logger = create_logger('dem_utils', 'sh', 'INFO')

# Params
id_col = 'pair'
lsuffix = 'd1'
rsuffix = 'd2'
dem_name = 'dem_name'
dem_path = 'dem_filepath'
combo_dens = 'combo_dens'
date_diff = 'date_diff'
doy_diff = 'DOY_diff'
inters_geom = 'inters_geom'
ovlp_perc = 'aoi_ovlp_perc'
rank = 'rank'
mtp = 'matchtag_filepath'

# Existing field names
# acqdate = 'acquisitio'
# acqdate = 'acqdate1'
acqdate = 'ACQDATE1'
# filepath = 'local_file' #'fileurl'
filepath = get_filepath_field()
LOCATION = 'LOCATION'
orig_id_col = 'PAIRNAME'
PAIRNAME = 'PAIRNAME'
catalogid1 = 'catalogid1'

# Created field names
mtp_clipped = 'mtp_clipped'
mtp_clipped1 = '{}_{}'.format(mtp_clipped, lsuffix)
mtp_clipped2 = '{}_{}'.format(mtp_clipped, rsuffix)
dem_path1 = '{}_{}'.format(dem_path, lsuffix)
dem_path2 = '{}_{}'.format(dem_path, rsuffix)
orig_id_left = '{}_{}'.format(orig_id_col, lsuffix)
orig_id_right = '{}_{}'.format(orig_id_col, rsuffix)
mtp1 = '{}_{}'.format(mtp, lsuffix)  # 'matchtag_path_d1'
mtp2 = '{}_{}'.format(mtp, rsuffix)  # 'matchtag_path_d2'
acqdate1 = '{}_{}'.format(acqdate, lsuffix)
acqdate2 = '{}_{}'.format(acqdate, rsuffix)
filepath1 = '{}_{}'.format(filepath, lsuffix)
filepath2 = '{}_{}'.format(filepath, rsuffix)


#%% Set up
# Inputs
# out_dir = r'V:\pgc\data\scratch\jeff\ms\2020may12\footprints'
# out_name = 'aoi1_dem_fps_danco'
# out_shp = os.path.join(out_dir, '{}.shp'.format(out_name))
# # dem_ranking_sel_out = os.path.join(out_dir, '{}_rankings.shp'.format(out_name))
# # out_name = 'aoi1_dem_fps.gpkg'
# # out_layer = 'ao1_dem_selection_danco'
# out_catalogids = os.path.join(out_dir, '{}_catalogids.txt'.format(out_name))
# aoi_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\aois\aoi1.shp'
# aoi_ovlp_perc_thresh = 0.50
# dem_fp = None
# months = [5, 6, 7, 8, 9, 10]
# multispec = True
# density_thresh = 0.25
# n_select = 1
# select_offset = 1 # to not select the highest ranked


def dayofyear_diff(d1, d2):
    doy1 = pd.to_datetime(d1).dt.dayofyear
    doy2 = pd.to_datetime(d2).dt.dayofyear
    doy_diff = abs(doy1 - doy2)
    
    return doy_diff


def rank_dem_pair(density, ovlp_perc, date_diff, doy_diff):
    density_score = np.interp(density, (0, 1), (0, 10))
    ovlp_perc_score = np.interp(ovlp_perc, (0, 1), (0, 10))
    date_diff_score = np.interp(date_diff, (0, 700), (0, 10))
    doy_score = np.interp(-doy_diff, (-100, 0), (0, 10))
    
    score = ((density_score * 2) + ovlp_perc_score + date_diff_score + doy_score)*2
    
    return round(score, 2)


def data_selection(aoi_p, out_dir=None,
                   out_ints=None,
                   out_fps=None,
                   out_ids=None,
                   aoi_ovlp_perc_thresh=None,
                   dem_fp=None,
                   months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                   multispec=True,
                   intrack=False,
                   res=None,
                   n_select=None,
                   select_offset=0):

    if out_dir:
        out_dir = Path(out_dir)
        aoi_name = Path(aoi_p).stem
        if out_ints is None:
            out_ints = out_dir / '{}_selected_ints.shp'.format(aoi_name)
        if out_fps is None:
            out_fps = out_dir / '{}selection_fps.shp'.format(aoi_name)
        if out_ids is None:
            out_ids = out_dir / '{}selected_ids.txt'.format(aoi_name)

    #%% Select AOI DEMs
    logger.info('Identifying DEMs that meet intial criteria...')
    dems = dem_selector(aoi_p,
                        DEM_FP=dem_fp,
                        MONTHS=months,
                        DATE_COL=acqdate,
                        MULTISPEC=multispec,
                        LOCATE_DEMS=False,
                        INTRACK=intrack,
                        RES=res,
                        strips=True)

    logger.info('Loading AOI...')
    aoi = gpd.read_file(aoi_p)
    if aoi.crs != dems.crs:
        dems = dems.to_crs(aoi.crs)

    # Create fields for full path to DEM and associated matchtag.tif
    if platform.system() == 'Windows':
        dems[dem_path] = dems[LOCATION].apply(lambda x: nunatak2windows(x))
    else:
        dems[dem_path] = dems[LOCATION]
    # dems[dem_path] = dems.apply(lambda x: get_dem_path(x[filepath],
    #                                                    x[dem_name]), axis=1)
    dems[mtp] = dems.apply(lambda x: get_matchtag_path(x[dem_path]), axis=1)

    #%% Clip matchtags
    logger.info('Clipping {:,} matchtags to AOI...'.format(len(dems)))
    dems[mtp_clipped] = clip_rasters(aoi_p, list(dems[mtp]), in_mem=True,
                                     skip_srs_check=True)

    #%% Rank DEMs - Density
    logger.info('Ranking DEM pairs...')
    # Get overlap percentages with each other and with their intersections
    # and an AOI
    logger.debug('Identifying overlapping DEMs and computing area and percent '
                 'overlap...')
    dem_ovlp = dems2dems_ovlp(dems, name=PAIRNAME)
    logger.debug('Computing area and percent overlap with AOI for '
                 '{:,} intersections...'.format(len(dem_ovlp)))
    dem_ovlp = dems2aoi_ovlp(dem_ovlp, aoi)
    if aoi_ovlp_perc_thresh:
        dem_ovlp = dem_ovlp[dem_ovlp[ovlp_perc] >= aoi_ovlp_perc_thresh]

    #%%
    # Matchtag density
    logger.debug('Computing matchtag density...')

    combo_densities = []
    for i, row in tqdm(dem_ovlp.iterrows(), total=len(dem_ovlp)):
        cd = combined_density(row[mtp_clipped1], row[mtp_clipped2], row['inters_geom'],
                              # clip=True,
                              in_mem_epsg=dem_ovlp.crs.to_epsg())
        combo_densities.append(cd)
    dem_ovlp[combo_dens] = combo_densities
    logger.info('Combined matchtag density computed.')

    #%% Rank DEMs - Dates
    logger.debug('Calculating total number of days between DEM pairs...')
    # Number of days between
    dem_ovlp[date_diff] = abs(pd.to_datetime(dem_ovlp[acqdate1]) -
                              pd.to_datetime(dem_ovlp[acqdate2])) / \
                          datetime.timedelta(days=1)

    # Number of days between regardless of year
    logger.debug('Calculating number of days without year between DEM pairs...')
    dem_ovlp[doy_diff] = dayofyear_diff(dem_ovlp[acqdate1], dem_ovlp[acqdate2])

    dem_rankings = copy.deepcopy(dem_ovlp)
    dem_ovlp = None

    dem_rankings[rank] = dem_rankings.apply(
        lambda x: rank_dem_pair(x[combo_dens], x[ovlp_perc],
                                x[date_diff], x[doy_diff]), axis=1)

    #%% Rank DEMS - Sensor
    #%% Select DEMs
    dem_rankings.sort_values(by=rank, ascending=False, inplace=True)
    if n_select:
        selection = dem_rankings.iloc[select_offset:n_select+select_offset]
    else:
        selection = dem_rankings

    summary_cols = ['DEM_ID_d1', 'DEM_ID_d2',
                    'ovlp_area_sqkm', 'ovlp_perc',
                    'aoi_ovlp_perc', 'combo_dens',
                    'date_diff', 'DOY_diff', 'rank']
    # dem_rankings_summary = dem_rankings[summary_cols]
    selection_summary = selection[summary_cols]
    logger.info('Selection:\n{}'.format(selection_summary))

    #%% Write out selection
    # Write filepaths out
    logger.info('Writing DEM source catalogids to file: '
                '{}'.format(out_ids))
    # TODO: Add support for getting both images in crosstrack pair
    # Get both catalogid1 field names
    catalogid_fields = [cf for cf in list(selection)
                        if catalogid1 in cf]
    # Get all catalogids in those field names
    selected_catids = [cid for fld in catalogid_fields
                       for cid in list(selection[fld])]
    # Write catalogids to file
    with open(out_ids, 'w') as outtxt:
        for catid in selected_catids:
            outtxt.write('{}\n'.format(catid))

    # Write intersection as files
    logger.info('Writing intersection footprint to file: '
                '{}'.format(out_ints))
    # remove_unused_geometries(selection).to_file(out_ints)
    write_gdf(remove_unused_geometries(selection), out_ints, )
    # Write both footprint as file
    pns = np.array([list(selection[orig_id_left]),
                    list(selection[orig_id_right])]).flatten()
    orig_fps = dems[dems[orig_id_col].isin(pns)]

    # selected_footprints_out = os.path.join(out_dir, out_name)
    logger.info('Writing original footprints to file: '
                '{}'.format(out_fps))
    write_gdf(remove_unused_geometries(orig_fps), out_fps)
    # remove_unused_geometries(orig_fps).to_file(out_shp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--aoi',)
    parser.add_argument('--out_dir', type=os.path.abspath,
                        help='Path to directory to write intersections '
                             'and footprints to.')
    parser.add_argument('--out_ints', type=os.path.abspath,
                        help='Path to write intersections to.')
    parser.add_argument('--out_fps', type=os.path.abspath,
                        help='Path to write footprints to.')
    parser.add_argument('--aoi_ovlp_perc_thresh', type=float,
                        help='Minimum percent of overlap of intersection and '
                             'AOI to keep.')
    parser.add_argument('--dem_fp', type=os.path.abspath,
                        help='Path to alternative footprint to use, rather '
                             'than sandwich tables.')
    parser.add_argument('--months', nargs='+',
                        default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                        help='Months to include.')
    parser.add_argument('ms', '--multispectral', action='store_true',
                        help='Limit to multispectral only.')
    parser.add_argument('--intrack', action='store_true',
                        help='Limit to only intrack DEMs')
    parser.add_argument('--resolution', type=float, choices=[0.5, 2.0],
                        help='Limit to specified resolution.')
    parser.add_argument('--n_select', type=int,
                        help='Number of intersections to keep.')
    parser.add_argument('--select_offset', type=int, default=0,
                        help='Offset from best intersection to start with. '
                             'This can be used on a second run to avoid '
                             'getting the same intersections again.')

    import sys
    # sys.argv = [r'C:\code\pgc-code-all\rts\data_selection.py',
    #             '--aoi',
    #             r'E:\disbr007\umn\accuracy_assessment\mj_ward1\aoi\mj_ward1_3413.shp',
    #             '--out_dir',
    #             r'E:\disbr007\umn\accuracy_assessment\mj_ward1\data',
    #             '--months', '8',
    #             '--multispec',
    #             '--intrack',
    #             '--resolution', '2.0',
    #             '--aoi_ovlp_perc_thresh', '0.8']

    args = parser.parse_args()

    aoi = args.aoi
    out_dir = args.out_dir
    out_ints = args.out_ints
    out_fps = args.out_fps
    aoi_ovlp_perc_thresh = float(args.aoi_ovlp_perc_thresh)
    dem_fp = args.dem_fp
    months = args.months
    multispec = args.multispec
    intrack = args.intrack
    res = args.resolution
    n_select = args.n_select
    select_offset = args.select_offset

    data_selection(aoi_p=aoi,
                   out_ints=out_ints,
                   out_fps=out_fps,
                   out_dir=out_dir,
                   aoi_ovlp_perc_thresh=aoi_ovlp_perc_thresh,
                   dem_fp=dem_fp,
                   months=months,
                   multispec=multispec,
                   intrack=intrack,
                   res=res,
                   n_select=n_select,
                   select_offset=select_offset)