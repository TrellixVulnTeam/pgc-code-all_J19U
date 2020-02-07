# -*- coding: utf-8 -*-
"""
Created on Tue May 21 11:25:36 2019

@author: disbr007

Get percentage overlap for each footprint over *single* AOI polygon
"""

import os, argparse
import geopandas as gpd

### Define paths: index (or initial select), AOI, project folder
#project_path = r'E:\disbr007\UserServicesRequests\Projects\_nnunez\project_files'
##aoi_path = os.path.join(project_path, r'AWS_S6_10kmBuffer\AWS_S6_10kmBuffer.shp')
#aoi_path = os.path.join(project_path, 'aoi_prj.shp')
#index_path = os.path.join(project_path, r'initial_selection.shp')# already intersected for dev
#out_overlap_path = os.path.join(project_path, 'selection_aoi_overlap.shp')

def determine_overlap(aoi_path, index_path, percent_ovlp, max_cloudcover):
    
    ## Global parameters
    # Path and names
    project_path = os.path.dirname(aoi_path)
    aoi_name = os.path.basename(aoi_path).split('.')[0]
    out_path = os.path.join(project_path, '{}_ovlp.shp'.format(aoi_name))
        
    driver = 'ESRI Shapefile'
        
    ## Open AOI layer, deal with projection
    # Get total area of AOI
    aoi = gpd.read_file(aoi_path, driver=driver)
    aoi_feat = aoi[0:]
    aoi_area = aoi_feat.geometry.area[0]
      
    # Open footprints layer
    idx = gpd.read_file(index_path, driver=driver)
    if max_cloudcover:
        idx = idx[idx.CLOUDCOVER <= max_cloudcover]
    
    # Ensure projections match - if not reproject
    if aoi.crs != idx.crs:
        idx = idx.to_crs(aoi.crs)
    
    ## Calculate area of overlap with AOI for each footprint, save to new field  
    # Get all intersections
    intersections = gpd.overlay(idx, aoi, how='intersection')
    # Determine overlap percentage
    intersections['ovlp_perc'] = (intersections.geometry.area / aoi_area).round(decimals=2)*100
    # Join back to oringal footprint geometries
    idx = idx.set_index('SCENE_ID').join(intersections[['SCENE_ID', 'ovlp_perc']].set_index('SCENE_ID'))
    
    # Limit to minimum percent overlap, if specified
    if percent_ovlp:
        idx = idx[idx.ovlp_perc >= percent_ovlp]
    
    ## Write footprint to new file with overlap percentage column
    idx.reset_index(inplace=True)
    idx.to_file(out_path, driver=driver)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('aoi', type=str, help='Shapefile of area of interest.')
    parser.add_argument('footprint_layer', type=str, help='Footprint shapefile to use.')
    parser.add_argument('-p', '--percent_overlap', dest="percent_overlap", default=0, type=float, help='Minimum percentage overlap to write. e.g.: 50')
    parser.add_argument('-c', '--max_cloudcover', dest='max_cloudcover', default=1.0, type=float, help='Max cloudcover. e.g.: 0.20')
    args = parser.parse_args()
    
    aoi_path = os.path.abspath(args.aoi)
    fp_lyr_path = os.path.abspath(args.footprint_layer)
    percent_ovlp = args.percent_overlap
    max_cloudcover = args.max_cloudcover
    
    determine_overlap(aoi_path, fp_lyr_path, percent_ovlp, max_cloudcover)
    
    
    










