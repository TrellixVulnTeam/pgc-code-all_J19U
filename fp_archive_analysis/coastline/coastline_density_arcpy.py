# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 11:54:10 2019

@author: disbr007
"""

import arcpy
import logging, sys
#from tqdm import tqdm

#
##### Set up environment
#arcpy.env.OverwriteOutput = True
#arcpy.env.workspace = r'C:\Users\disbr007\projects\coastline\coastline.gdb'
#
### Paths
#src = 'mfp'
#grid_n = 'density_grid_one_deg_16x16_10km'
#cand_n = '{}_global_coastline_candidates_1'.format(src)
#density_n = 'mfp_density'

def coastline_density(src, final_candidates, grid, density_name):
    '''
    grid: polygon grid to count final_candidates
    density_name: name of density feature class
    '''
    #### Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    
    # Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
    # The following inputs are layers or table views: "density_grid_sample_16x16_1", "mfp_subset"
    logger.info('Performing spatial join...')
    density_int_n = '{}_sjoin_intermed'.format(src) ## intermediate feature class in memory
    arcpy.SpatialJoin_analysis(target_features=grid, 
                               join_features=final_candidates, 
                               out_feature_class=density_int_n, 
                               join_operation="JOIN_ONE_TO_MANY", join_type="KEEP_ALL", 
                               match_option="INTERSECT")
    
    logger.info('Dissolving...')
    arcpy.Dissolve_management(in_features=density_int_n,
                              out_feature_class=density_name,
                              dissolve_field='TARGET_FID',
                              statistics_fields=[['TARGET_FID', 'COUNT']])
