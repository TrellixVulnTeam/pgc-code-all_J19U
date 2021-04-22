# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 11:35:49 2020

@author: disbr007
"""
import numpy as np
from pathlib import Path
import os
import platform
import re

from osgeo import gdal
import pandas as pd
import geopandas as gpd
import shapely

# from dem_utils.dem_selector import dem_selector
from misc_utils.gdal_tools import clip_minbb
from misc_utils.logging_utils import create_logger
from misc_utils.raster_clip import clip_rasters
from misc_utils.RasterWrapper import Raster


logger = create_logger(__name__, 'sh', 'INFO')


def dem_pair(name1, name2):
    """Create name for pair of DEMs"""
    names = sorted([name1, name2])
    pairname = '{}-{}'.format(names[0], names[1])

    return pairname


def intersect_pair(geom1, geom2):
    """Clip the left geometry by the right"""
    gdf1 = gpd.GeoDataFrame(geometry=[geom1])
    gdf2 = gpd.GeoDataFrame(geometry=[geom2])
    clipped = gpd.overlay(gdf1, gdf2, how='intersection')

    return clipped.geometry


def calc_sqkm(geom):
    return geom.area / 10e6


def calc_ovlp_perc(geom1, geom2, ovlp_geom):
    ovlp_perc = ovlp_geom.area / (geom1.area + geom2.area)
    return round(ovlp_perc, 2)


def dems2dems_ovlp(dems, 
                   name='PAIRNAME',
                   combo_name='pair', intersect_geom='inters_geom',
                   lsuffix='d1', rsuffix='d2',
                   ovlp_area_name='ovlp_area', ovlp_perc_name='ovlp_perc',
                   sqkm=True, drop_orig_geom=True):
    """
    Compute overlap between all DEM footprints that intersect in dems geodataframe.

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
    # lsuffix = 'd1'
    # rsuffix = 'd2'
    name_left = '{}_{}'.format(name, lsuffix)
    name_right = '{}_{}'.format(name, rsuffix)
    geom_left = '{}_{}'.format(new_geom_col, lsuffix)
    geom_right = '{}_{}'.format(new_geom_col, rsuffix)
    # intersect_geom = 'inters_geom'
    ovlp_area_sqkm = '{}_sqkm'.format(ovlp_area_name)
    # ovlp_perc_dems = 'ovlp_perc_dems'

    # Save each features geometry to colum to allow accessing both left and right geom
    dems[new_geom_col] = dems.geometry

    # Join with self, one record per intersection in resulting df
    sj = gpd.sjoin(dems, dems, lsuffix=lsuffix, rsuffix=rsuffix)

    # Drop self joins
    sj = sj[sj['{}_{}'.format(name, lsuffix)] != sj['{}_{}'.format(name, rsuffix)]]

    # Create ID column for each pair
    sj[combo_name] = sj.apply(lambda x: dem_pair(x[name_left], x[name_right]), axis=1)

    # Set index as combined name
    sj.set_index(combo_name, inplace=True)

    # Drop duplicates where dem1 -> dem2 == dem2 -> dem1 (reciprocal matches)
    sj = sj[~sj.index.duplicated(keep='first')]
    # sj = sj.drop_duplicates(subset=combo_name, keep='first')

    # Get intersection area, calculate sqkm, % overlap
    sj[intersect_geom] = sj.apply(lambda x: intersect_pair(x[geom_left], x[geom_right]), axis=1)
    sj = sj.set_geometry(intersect_geom)
    sj[ovlp_area_name] = sj.geometry.area
    if sqkm:
        sj[ovlp_area_sqkm] = sj.apply(lambda x: calc_sqkm(x[intersect_geom]), axis=1)
    sj[ovlp_perc_name] = sj.apply(lambda x: calc_ovlp_perc(x[geom_left], x[geom_right], x[intersect_geom]), axis=1)

    if drop_orig_geom:
        sj = sj.drop(columns=[geom_left, geom_right])

    return sj


def dems2aoi_ovlp(dems, aoi, aoi_ovlp_area_col='aoi_ovlp_area', aoi_ovlp_perc_col='aoi_ovlp_perc'):
    """Compute overlap between dem footprints and an aoi"""
    dems_idx_name = dems.index.name
    if dems_idx_name is None:
        dems_idx_name = 'index'

    aoi_ovlp = gpd.overlay(dems.reset_index(), aoi, how='intersection')
    aoi_ovlp.set_index(dems_idx_name, inplace=True)
    aoi_ovlp[aoi_ovlp_area_col] = aoi_ovlp.geometry.area.apply(
                                    lambda x: round(x, 5))
    dems = pd.merge(dems, aoi_ovlp[aoi_ovlp_area_col],
                    left_index=True, right_index=True)
    dems[aoi_ovlp_perc_col] = dems[aoi_ovlp_area_col].apply(
                                lambda x: x / aoi.geometry.area.values[0])
    # dems[aoi_ovlp_area_col] = [round(a, 2) for a in list(aoi_ovlp.geometry.area)]
    # dems[aoi_ovlp_perc_col] = [round(p, 2) for p in list(aoi_ovlp.geometry.area / aoi.geometry.area.values[0])]

    return dems


def compute_density(mt_p, aoi_p):
    logger.debug('Computing density...')
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

    return round(density, 2)


def combined_density(mt1, mt2, aoi, in_mem_epsg=None, clip=False, out_path=None):
    """Get density for two matchtags over AOI"""
    # Ensure both matchtags exist
    # if not os.path.exists(mt1) or not os.path.exists(mt2):
    #     for mt in [mt1, mt2]:
    #         if not os.path.exists(mt):
    #             logger.error('Matchtag file not found: {}'.format(mt))
    #     return -9999
    
    # Determine type of aoi
    # If shapely geometry, save to in-memory file
    if isinstance(aoi, (shapely.geometry.polygon.Polygon, shapely.geometry.MultiPolygon)):
        gdf = gpd.GeoDataFrame(geometry=[aoi], crs='epsg:{}'.format(in_mem_epsg))
        aoi = r'/vsimem/combined_density_temp.shp'
        gdf.to_file(aoi)
    
    if clip:
        logger.debug('Clipping matchtags before comparing...')
        mt1, mt2 = clip_rasters(aoi, [mt1, mt2], in_mem=True)
    
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

    return round(combo_dens.values[0], 2)


def get_filepath_field():
    OS = platform.system()
    if OS == 'Windows':
        filepath_field = 'LOCATION'
    elif OS == 'Linux':
        filepath_field = 'LOCATION'
    else:
        logger.error('Unknown operating system: {}'.format(OS))
    
    return filepath_field


def nunatak2windows(filepath):
    windows_path = filepath.replace('/mnt', 'V:').replace('/', '\\')
    
    return windows_path


def get_dem_path(dem_dir, dem_name):
    return os.path.join(dem_dir, dem_name)


def get_matchtag_path(dem_path):
    return dem_path.replace('dem.tif', 'matchtag.tif')


def get_bitmask_path(dem_path):
    bm_p = os.path.join(
        os.path.dirname(dem_path),
        os.path.basename(dem_path).replace('dem', 'bitmask')
    )

    return bm_p


def get_aux_file(dem_path, aux_file):
    sfx = {'bitmask': 'bitmask.tif',
           'dem': 'dem.tif',
           '10m_shade': 'dem_10m_shade.tif',
           '10m_shade_masked': 'dem_10m_shade_masked.tif',
           'matchtag': 'matchtag.tif',
           'ortho': 'ortho.tif',
           'meta': 'meta.txt',}

    aux_path = dem_path.replace('dem.tif', sfx[aux_file])

    return aux_path


def get_dem_image1_id(meta_path):
    image1_ids = set()
    with open(meta_path) as src:
        content = src.readlines()
        for line in content:
            if 'Image 1=' in line:
                pat = re.compile('Image 1=(.*)')
                match = pat.search(line)
                if match:
                    scene1_path = Path(match.group(1))
                    image1_id = (scene1_path.stem.split('_')[2])
                    image1_ids.add(image1_id)
    if len(image1_ids) > 1:
        logger.warning('Multiple values found for Image 1 in {}'.format(meta_path))
    elif len(image1_ids) == 0:
        logger.warning('No values found for Image 1 in {}'.format(meta_path))
    else:
        return image1_id


def difference_dems(dem1, dem2, out_dem=None, in_mem=False):
    logger.debug('Difference DEMs:\nDEM1: {}\nDEM2:{}'.format(dem1, dem2))
    clipped = clip_minbb([dem1, dem2], in_mem=True)
    dem1_clipped = Raster(clipped[0])
    dem2_clipped = Raster(clipped[1])

    diff = dem1_clipped.MaskedArray - dem2_clipped.MaskedArray

    if out_dem:
        logger.debug('Writing difference to: {}'.format(out_dem))
        dem1_clipped.WriteArray(diff, out_path=out_dem)

    return out_dem
