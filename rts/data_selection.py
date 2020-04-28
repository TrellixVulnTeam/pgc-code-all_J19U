# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 11:35:49 2020

@author: disbr007
"""
import matplotlib.pyplot as plt
import numpy as np

from osgeo import gdal
import geopandas as gpd

from dem_utils.dem_selector import dem_selector
from misc_utils.logging_utils import create_logger
from misc_utils.raster_clip import clip_rasters
from misc_utils.RasterWrapper import Raster


logger = create_logger(__name__, 'sh', 'DEBUG')
plt.style.use("spyder4")


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


def dems2aoi_ovlp(dems, aoi, aoi_ovlp_area_col='aoi_ovlp_area', aoi_ovlp_perc_col='aoi_ovlp_perc'):
    aoi_ovlp = gpd.overlay(dems, aoi, how='intersection')
    # aoi_ovlp['aoi_ovlp_area'] = aoi_ovlp.geometry.area
    # aoi_ovlp['aoi_ovlp_perc'] = aoi_ovlp.geometry.area / aoi.geometry.area.values[0]

    dems[aoi_ovlp_area_col] = aoi_ovlp.geometry.area
    dems[aoi_ovlp_perc_col] = aoi_ovlp.geometry.area / aoi.geometry.area.values[0]
    
    return dems


def remove_unused_geometries(df):
    remove = [x for x in list(df.select_dtypes(include='geometry')) if x != df.geometry.name]
    
    return df.drop(columns=remove)


def compute_density(mt_p, aoi_p):
    logger.info('Computing density...')
    aoi = gpd.read_file(aoi_p)
    if len(aoi) == 1:
        geom_area = aoi.geometry.area
    else:
        logger.warning('Multiple features found in AOI provided. Using first for density calculation.')
        geom_area = aoi.geometry.area[0]
    
    ds = gdal.Open(mt_p)
    b = ds.GetRasterBand(1)
    gtf = ds.GetGeoTransform()
    matchtag_res_x = gtf[1]
    matchtag_res_y = gtf[5]
    matchtag_ndv = b.GetNoDataValue()
    data = b.ReadAsArray()
    err = gdal.GetLastErrorNo()
    if err != 0:
        raise RuntimeError("Matchtag dataset read error: {}, {}".format(gdal.GetLastErrorMsg(), mt_p))
    else:
        data_pixel_count = np.count_nonzero(data != matchtag_ndv)
        data_area = abs(data_pixel_count * matchtag_res_x * matchtag_res_y)
        density = data_area / geom_area
        data = None
        ds = None
    
    return density


def combined_density(mt1, mt2, aoi, clip=False, out_path=None):
    if clip:
        mt1, mt2 = clip_rasters(intersection_out, [mt1, mt2], in_mem=True)
    
    if not out_path:
        # compute combined matchtag in memory only
        out_path = r'/vsimem/temp_comb_mt.tif'
    # Read matchtag arrays
    m1 = Raster(mt1)
    arr1 = m1.Array
    m2 = Raster(mt2)
    arr2 = m2.Array
    if arr1.shape != arr2.shape:
        logger.warning("""Matchtag arrays do not match. 
                       Must be clipped before computing combined density.""")
    
    # Create new array, 1 if both matchtags were 1, otherwise 0.
    combo_mt = np.where(arr1 + arr2 == 2, 1, 0)
    
    # Write new combined matchtag array
    m1.WriteArray(combo_mt, out_path)
    
    # Compute density
    combo_dens = compute_density(out_path, aoi)

    return combo_dens.values[0]


#%% Get overlap percentages with each other and AOI
dem_ovlp = dems2dems_ovlp(dems)
dem_ovlp = dems2aoi_ovlp(dem_ovlp, aoi)

# Sort
dem_ovlp = dem_ovlp.sort_values(by='ovlp_area', ascending=False)

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
logger.info('DEM1: {}'.format(filepath1))
logger.info('DEM2: {}'.format(filepath2))

# Write intersection as files
intersection_out = r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_test_int.shp'
logger.info('Writing intersection footprint to file: {}'.format(intersection_out))
remove_unused_geometries(sel).to_file(intersection_out)

# Write both footprints as file
orig_id_left = '{}_{}'.format(orig_id_col, lsuffix)
orig_id_right = '{}_{}'.format(orig_id_col, rsuffix)
pns = [sel[orig_id_left].iloc[0], sel[orig_id_right].iloc[0]]
orig_fps = dems[dems['pairname'].isin(pns)]

selected_footprints_out = r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_test_orig_fps.shp'
logger.info('Writing original footprints to file: {}'.format(selected_footprints_out))
remove_unused_geometries(orig_fps).to_file(selected_footprints_out)

#%% Clip matchtags 
# in memory and calculate density in AOI
dem1_p = r'E:\disbr007\umn\ms\selection\dems\SETSM_WV02_20150811_10300100455CA700_1030010045D2E500_seg4_2m_v3.0\SETSM_WV02_20150811_10300100455CA700_1030010045D2E500_seg4_2m_v3.0_dem.tif'
dem2_p = r'E:\disbr007\umn\ms\selection\dems\SETSM_WV02_20140818_1030010035755C00_10300100360BC800_seg3_2m_v3.0\SETSM_WV02_20140818_1030010035755C00_10300100360BC800_seg3_2m_v3.0_dem.tif'
mt1_p = dem1_p.replace('dem.tif', 'matchtag.tif')
mt2_p = dem2_p.replace('dem.tif', 'matchtag.tif')

#%% Combined density
combo_dens = combined_density(mt1_p, mt2_p, intersection_out, clip=True)
