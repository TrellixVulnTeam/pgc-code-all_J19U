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


def colormap_img(tif, cmap, out_img, of=None, exact=False, overwrite=False):
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
    # TODO: Check this logic for overwriting...
    if overwrite or not os.path.exists(out_img):
        cmd = ['gdaldem', 'color-relief', tif, cmap, out_img, 
                '-nearest_color_entry', '-of', of, '-alpha']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        logger.info(out)
        logger.debug(err)
    else:
        out_img = None

    return out_img


def main(args):
    parent_dir = args.parent_directory
    cmap = args.cmap_txt
    of = args.out_format
    suffix = args.suffix
    dryrun = args.dryrun
    
    # Determine appropriate output extension given the 'of'
    ext_lut = {'PNG': 'png',
               'JP2OpenJPEG': 'jp2',
               'GTiff': 'tif',}
    out_ext = ext_lut[of]
    
    # Locate cmap file - from arg or check current working directory
    if cmap is None:
        cwd = os.getcwd()
        cmap = os.path.join(cwd, r'cmap.txt')
    
    # Collect 10m DEM stack count tifs
    tifs = []
    for root, dirs, files in os.walk(parent_dir, topdown=True):
        dirs[:] = [d for d in dirs if d != 'subtiles']
        for f in files:
            if f.endswith(suffix):
                tifs.append(os.path.join(root, f))
                
    # Create a IMG with colors corresponding to RGB values color_map text file
    for tif in tifs:
        tif_dir = os.path.dirname(tif)
        tif_name = os.path.basename(tif).split('.')[0]
        out_img = os.path.join(tif_dir, '{}_cmap.{}'.format(tif_name, out_ext))
        logger.info('Creating colormap {} for: {}'.format(of, tif))
        if dryrun:
            continue
        colormap_img(tif, cmap, out_img=out_img, of=of)
        # TODO: Remove this - just for convenience for Paul
        # Do move 
        dst = r'V:\pgc\users\jeff\for_paul\arcticdem_mosaic_cmaps_2mv4'
        copy_name = os.path.basename(out_img)
        copy_sd = os.path.basename(os.path.dirname(out_img))
        copy_loc  = os.path.join(dst, copy_sd, copy_name)
        if not os.path.exists(os.path.join(dst, copy_sd)):
            os.makedirs(os.path.join(dst, copy_sd))
        import shutil
        logger.info('Copying cmap file to: {}'.format(copy_loc))
        shutil.copy2(out_img, copy_loc)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('parent_directory', type=os.path.abspath,
                        help='Directory containing "*_N.tif" files to create PNG colormaps of.')
    parser.add_argument('--cmap_txt', type=os.path.abspath, default=None,
                        help=""""Path to text file containing DEM values -> RGB-Alpha values.
                                 Defaults to looking for 'cmap.txt' in the current directory.""")
    parser.add_argument('--out_format', type=str,
                        help="""Output format, must be a GDAL raster driver: 
                                https://gdal.org/drivers/raster/index.html""")
    parser.add_argument('--suffix', type=str,
                        help='String to limit files process, e.g. "10m_N.tif"')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print actions without running.')
    
    args = parser.parse_args()
    
    main(args)
    