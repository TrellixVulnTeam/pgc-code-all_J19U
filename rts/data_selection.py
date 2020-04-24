# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 11:35:49 2020

@author: disbr007
"""
import matplotlib.pyplot as plt

import geopandas as gpd

from dem_utils.dem_selector import dem_selector
from misc_utils.logging_utils import create_logger, create_module_loggers

logger = create_logger(__name__, 'sh', 'DEBUG')
plt.style.use("spyder4")
# logger = create_module_loggers('sh', 'INFO')

#%% Select DEM footprints over AOI
# Inputs
aoi_p = r'E:\disbr007\umn\ms\selection\aoi\aoi1.shp'
dem_fp = r'E:\disbr007\arctic_dem\ArcticDEM_Strip_Index_Rel7\ArcticDEM_Strip_Index_Rel7.shp'
months = [5, 6, 7, 8, 9, 10]
multispec = True
density_thresh = 0.5

dems = dem_selector(aoi_p,
                    DEM_FP=dem_fp,
                    MONTHS=months,
                    DATE_COL='acquisit_1',
                    MULTISPEC=multispec,
                    LOCATE_DEMS=False)
                    # DENSITY_THRESH=density_thresh)

aoi = gpd.read_file(aoi_p)
if aoi.crs != dems.crs:
    dems = dems.to_crs(aoi.crs)
    # aoi = aoi.to_crs(dems.crs)

#%% Fxn
def dem_pair(name1, name2):
    # Creat name for pair of DEMs
    names = sorted([name1, name2])
    pairname = '{}_{}'.format(names[0], names[1])
    
    return pairname


def clip_pair(geom1, geom2):
    # Clip the left geometry by the right
    gdf1 = gpd.GeoDataFrame(geometry=[geom1])
    gdf2 = gpd.GeoDataFrame(geometry=[geom2])
    clipped = gpd.overlay(gdf1, gdf2, how='intersection')
    
    return clipped.geometry


def calc_sqkm(geom):
    return geom.area / 10e6


def calc_ovlp_perc(geom1, geom2, ovlp_geom):
    ovlp_perc = ovlp_geom.area / (geom1.area + geom2.area)
    return round(ovlp_perc, 2)


def dems2dems_ovlp(dems, name='pairname', ovlp_area_name='ovlp_area', ovlp_perc_name='ovlp_perc',
                   sqkm=True, drop_orig_geom=True):
    """
    Computes overlap between all DEM footprints that intersect in dems geodataframe.
    
    Parameters
    ----------
    dems : gpd.GeoDataFrame
        GeoDataFrame of footprints
    name : str
        Name of column in dems to use as ID.
    ovlp_area_name : str
        Name of column to create to hold the area in units of projection.
    ovlp_perc_name : str
        Name of column to create to hold the percentage of overlap between each pair
    Returns
    -------
    gpd.GeoDataFrame : where the geometry is all of the intersections with 
                       area and percent overlap computed.
    """
    new_geom_col = 'new_geom_col'
    lsuffix = 'd1'
    rsuffix = 'd2'
    name_left = '{}_{}'.format(name, lsuffix)
    name_right = '{}_{}'.format(name, rsuffix)
    geom_left = '{}_{}'.format(new_geom_col, lsuffix)
    geom_right = '{}_{}'.format(new_geom_col, rsuffix)
    intersect_geom = 'inters_geom'
    ovlp_area_sqkm = '{}_sqkm'.format(ovlp_area_name)
    # ovlp_perc_dems = 'ovlp_perc_dems'
    
    # Save each features geometry to colum to allow accessing both left and right geom
    dems[new_geom_col] = dems.geometry
    
    # Join with self, one record per intersection in resulting df
    sj = gpd.sjoin(dems, dems, lsuffix=lsuffix, rsuffix=rsuffix)
    
    # Drop self joins
    sj = sj[sj['{}_{}'.format(name, lsuffix)]!=sj['{}_{}'.format(name, rsuffix)]]
    
    # Create ID column for each pair
    sj['pair'] = sj.apply(lambda x: dem_pair(x[name_left], x[name_right]), axis=1)
    # Drop duplicates where dem1 -> dem2 == dem2 -> dem1 (reciprocal matches)
    sj = sj.drop_duplicates(subset='pair', keep='first')
    
    # Get intersection area, calculate sqkm, % overlap
    sj[intersect_geom] = sj.apply(lambda x: clip_pair(x[geom_left], x[geom_right]), axis=1)
    sj = sj.set_geometry(intersect_geom)
    sj[ovlp_area_name] = sj.geometry.area
    if sqkm:
        sj[ovlp_area_sqkm]= sj.apply(lambda x: calc_sqkm(x[intersect_geom]), axis=1)
    sj[ovlp_perc_name] = sj.apply(lambda x: calc_ovlp_perc(x[geom_left], x[geom_right], x[intersect_geom]), axis=1)

    if drop_orig_geom:
        sj = sj.drop(columns=[geom_left, geom_right])
    
    return sj


def dems2aoi_ovlp(dems, aoi):
    aoi_ovlp = gpd.overlay(dems, aoi, how='intersection')
    aoi_ovlp['aoi_ovlp_area'] = aoi_ovlp.geometry.area
    aoi_ovlp['aoi_ovlp_perc'] = aoi_ovlp.geometry.area / aoi.geometry.area.values[0]

    dems['aoi_ovlp_area'] = aoi_ovlp.geometry.area
    dems['aoi_ovlp_perc'] = aoi_ovlp.geometry.area / aoi.geometry.area.values[0]
    
    return dems

#%% Get overlap percentages with each other and AOI
dem_ovlp = dems2dems_ovlp(dems)

# Sort
dem_ovlp = dem_ovlp.sort_values(by='ovlp_area')

df = dem_ovlp
# Select dems
orig_id_col = 'pairname'
id_col = 'pair'
filepath_col_base = 'fileurl'
lsuffix = 'd1'
rsuffix = 'd2'
#%% Plotting
# Select row
row = 0
sel = df.iloc[row:row+1]

# Get filepath (or url)
filepath_left = '{}_{}'.format(filepath_col_base, lsuffix)
filepath_right = '{}_{}'.format(filepath_col_base, rsuffix)
filepath1 = sel[filepath_left].iloc[0]
filepath2 = sel[filepath_right].iloc[0]

# Write intersection as file
# ToDO: write function to remove all non used geometry columns before writing
sel.drop(columns='geometry').to_file(r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_test_int.shp')
# Write both footprints as file
orig_id_left = '{}_{}'.format(orig_id_col, lsuffix)
orig_id_right = '{}_{}'.format(orig_id_col, rsuffix)
pns = [sel[orig_id_left].iloc[0], sel[orig_id_right].iloc[0]]
orig_fps = dems[dems['pairname'].isin(pns)]
orig_fps.drop(columns='new_geom_col').to_file(r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_test_orig_fps.shp')

# dem_ovlp = dems2aoi_ovlp(dem_ovlp, aoi)

# row = 4
# d1 = dem_ovlp['pairname_d1'].iloc[row]
# d2 = dem_ovlp['pairname_d2'].iloc[row]
# dem_sel = dems[dems['pairname'].isin([d1,d2])]
# intersection = dem_ovlp[dem_ovlp['pair']=='{}_{}'.format(d1, d2)]

fig, ax = plt.subplots(1,1)
# intersect[i:i+1].plot(column='ovlp_area', edgecolor='red', ax=ax, alpha=0.5)
sel.plot(color='blue', edgecolor='gray', ax=ax, linewidth=1)
orig_fps.plot(color='none', edgecolor='red', linewidth=1, alpha=0.4, ax=ax)
# .plot(color='red', alpha=0.5, ax=ax)
# dem_ovlp.plot(color='none', edgecolor='blue', linestyle='--', linewidth=0.3, ax=ax)
# aoi.plot(color='none', edgecolor='white', ax=ax)

#%% Clip matchtags 
# in memory and calculate density in AOI
# report average
# report average with NoData as 0