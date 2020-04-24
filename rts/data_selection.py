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
                    # DEM_FP=dem_fp,
                    MONTHS=months,
                    MULTISPEC=multispec,
                    DENSITY_THRESH=density_thresh)

aoi = gpd.read_file(aoi_p)
if aoi.crs != dems.crs:
    dems = dems.to_crs(aoi.crs)
    # aoi = aoi.to_crs(dems.crs)

#%% Calculate overlap area
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
    sj['pair'] = sj.apply(lambda x: dem_pair(x['objectid_{}'.format(lsuffix)], x['objectid_{}'.format(rsuffix)]), axis=1)
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


def dems2aoi_ovlp(dems, ovlp):
    aoi_ovlp = gpd.overlay(intersect, aoi, how='intersection')
    aoi_ovlp['aoi_ovlp_area'] = aoi_ovlp.geometry.area
    aoi_ovlp['aoi_ovlp_perc'] = aoi_ovlp.geometry.area / aoi.geometry.area.values[0]

    return aoi_ovlp

#%% Clip matchtags 
# in memory and calculate density in AOI
# report average
# report average with NoData as 0

#%% Plotting
# fig, ax = plt.subplots(1,1)

# dems.plot(column='num_gcps', edgecolor='white', alpha=0.5, legend=True, ax=ax)
# x.set_geometry('clipped').plot(color='blue', ax=ax)
# aoi.plot(color='none', edgecolor='red', linewidth=0.5, ax=ax)
for i in range(0, len(intersect)+1):
    fig, ax = plt.subplots(1,1)
    intersect[i:i+1].plot(column='ovlp_area', edgecolor='red', ax=ax, alpha=0.5)
    aoi.plot(color='none', edgecolor='white', ax=ax)
# aoi_ovlp.plot(color='blue', ax=ax)

