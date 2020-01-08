# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 14:13:57 2020

@author: disbr007
"""

import argparse
import logging
import os
import subprocess


# # Inputs
# parent_dir = r'E:\disbr007\temp\arctic_dem_cmap'
# cwd = os.getcwd()
# # cmap = os.path.join(cwd, r'cmap.txt')
# cmap = r'C:\temp\gdal_colormap\cmap.txt'
# dryrun = True


# Logging setup
logger = logging.getLogger('tif_color_ramp')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def colormap_png(tif, cmap, png_out, exact=False):
    """
    Calls gdaldem color-relief to create a PNG with colors corresponding to
    values in cmap text file.
    
    Parameters
    ----------
    tif : os.path.abspath
        Path to the existing tif file..
    cmap : os.path.abspath
        Text file containing tif values and RGBAlpha values in format:
            value R G B A.
    out_png : os.path.abspath 
        Path to create the new .png file at.
    exact : BOOLEAN
        True to match values in cmap file exactly, otherwise interpolate from
        closest values. 
        True == -exact_color_entry gdaldem flag
        False == -nearest_color_entry gdaldem flag

    Returns
    -------
    out_png : STR

    """
    cmd = ['gdaldem', 'color-relief', tif, cmap, png_out, 
            '-nearest_color_entry', '-of', 'PNG', '-alpha']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    logger.info(out)
    logger.debug(err)
    
    return png_out


def main(args):
    parent_dir = args.parent_directory
    cmap = args.cmap_txt
    dryrun = args.dryrun
    
    if cmap is None:
        cwd = os.getcwd()
        cmap = os.path.join(cwd, r'cmap.txt')
    
    # Collect 10m DEM stack count tifs
    stack_count_tifs = []
    for root, dirs, files in os.walk(parent_dir, topdown=True):
        dirs[:] = [d for d in dirs if d != 'subtiles']
        for f in files:
            if f.endswith('10m_N.tif'):
                stack_count_tifs.append(os.path.join(root, f))
                
    # Create a PNG with colors corresponding to RGB values color_map text file
    for tif in stack_count_tifs:
        tif_dir = os.path.dirname(tif)
        tif_name = os.path.basename(tif).split('.')[0]
        out_png = os.path.join(tif_dir, '{}_cmap.png'.format(tif_name))
        logger.info('Creating colormap PNG for: {}'.format(tif))
        if dryrun:
            continue
        colormap_png(tif, cmap, out_png=out_png)

        # cmd = ['gdaldem', 'color-relief', tif, cmap, png_out, 
        #         '-nearest_color_entry', '-of', 'PNG', '-alpha']
        # p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        # out, err = p.communicate()
        # logger.info(out)
        # logger.debug(err)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('parent_directory', type=os.path.abspath,
                        help='Directory containing "*_N.tif" files to create PNG colormaps of.')
    parser.add_argument('--cmap_txt', type=os.path.abspath, default=None,
                        help=""""Path to text file containing DEM values -> RGB-Alpha values.
                                 Defaults to looking for 'cmap.txt' in the current directory.""")
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without running.')
    
    args = parser.parse_args()
    
    main(args)
    