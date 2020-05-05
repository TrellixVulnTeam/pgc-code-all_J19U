# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 10:22:54 2020

@author: disbr007
"""
import argparse
import tarfile
import os
import subprocess

import geopandas as gpd
from tqdm import tqdm

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = proc.communicate()
    logger.info('Output: {}'.format(output))
    if error:
        logger.info('Err: {}'.format(error))
        logger.info('Command: {}'.format(command))

def get_dem_dst(dem_dir, tar_path):
    dem_name = os.path.basename(tar_path).replace('.tar.gz', '')
    dem_subdir = os.path.join(dem_dir, dem_name)
    dst_dem = os.path.join(dem_subdir, '{}_dem.tif'.format(dem_name))
    
    return dst_dem
    

def dl_arcticdem_strips(fp_p, dst_dir, url_fields=['fileurl'], log_file=None,
                        out_filepath_fld=None, out_fp=None):
    """Download and unzip ArcticDEM footprints"""
    if not log_file:
        log_file = os.path.join(dst_dir, 'wget_log.txt')
    
    # Create destination directories
    gz_dir = os.path.join(dst_dir, 'gz')
    dems_dir = os.path.join(dst_dir, 'dems')
    for subdir in [gz_dir, dems_dir]:
        if not os.path.exists(subdir):
            os.makedirs(subdir)
    if not os.path.exists(log_file):
        with open(log_file, 'w') as fp: 
            pass
    
    # Read footprint
    logger.info('Reading footprint...')
    fp = gpd.read_file(fp_p)
    
    # Get urls
    urls = set([ul for uf in url_fields for ul in list(fp[uf])])
    logger.info('URLs found: {}'.format(len(urls)))
    
    # Download urls
    logger.info('Downloading tarfiles: {}'.format(len(urls)))
    for url in tqdm(urls):
        # Check if destination file exists, either as a tarfile or dem
        dst_tar = os.path.join(gz_dir, os.path.basename(url))
        dst_dem = get_dem_dst(dems_dir, url)
        if os.path.exists(dst_tar) or os.path.exists(dst_dem):
            logger.debug('Destination file exists, skipping: {}'.format(os.path.basename(url)))
            continue
        # Download
        logger.debug('wget-ting: {}'.format(url))
        cmd = r"""wget --directory-prefix {} -o {} {}""".format(gz_dir, log_file, url)
        run_subprocess(cmd)
    
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # Unzip tarfiles
    gzs = [os.path.join(gz_dir, zf) for zf in os.listdir(gz_dir)]
    logger.info('Unzipping tarfiles: {}'.format(len(gzs)))
    for gz in tqdm(gzs):
        # Unzip to dems_dir
        dst_dem = get_dem_dst(dems_dir, gz)
        dem_subdir = os.path.join(dems_dir, os.path.splitext(os.path.basename(dst_dem))[0])
        if not os.path.exists(dem_subdir):
            os.makedirs(dem_subdir)
        if not os.path.exists(dst_dem):
            logger.debug('Unzipping: {}'.format(gz))
            with tarfile.open(gz, 'r:gz') as tar:
                tar.extractall(dem_subdir)
    
    # Add local filepath fields to footprint 
    if out_filepath_fld:
        for i, uf in enumerate(url_fields, 1):
            fp['{}{}'.format(out_filepath_fld, i)] = fp.apply(lambda x: get_dem_dst(dems_dir, x[uf]), axis=1)
    if out_fp:
        logger.info('Writing footprint with local filepaths to: {}'.format(out_fp))
        fp.to_file(out_fp)
    
    return fp
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_footprint', type=os.path.abspath,
                        help='Path to footprint with urls to download.')
    parser.add_argument('-d', '--destination_directory', type=os.path.abspath,
                        help="""Directory to download files to. Subdirectories for 
                                zipped and unzipped files will be created here.""")
    parser.add_argument('-urls', '--url_fields', nargs='+',
                        default=['fileurl'],
                        help='Field(s) in footprint with urls.')
    parser.add_argument('-lfp', '--local_filepath_field', type=str,
                         help='Optional, name of field to create with unzip tif locations.')
    parser.add_argument('-of', '--out_footprint', type=os.path.abspath,
                        help='Path to write footprint with added local_file_path field.')
    
    args = parser.parse_args()
    
    fp_p = args.input_footprint
    dst_dir = args.destination_directory
    url_fields = args.url_fields
    out_filepath_fld = args.local_filepath_field
    out_fp = args.out_footprint
    
    dl_arcticdem_strips(fp_p=fp_p,
                        dst_dir=dst_dir,
                        url_fields=url_fields,
                        out_filepath_fld=out_filepath_fld,
                        out_fp=out_fp)
    
# # Inputs
# fp_p = r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_fps.shp'
# dst_dir = r'E:\disbr007\umn\ms\selection\dems'
# url_fields = ['fileurl_d1', 'fileurl_d2']
# log_file = os.path.join(dst_dir, 'wget_log.txt')
# out_filepath_fld = 'local_filepath'
# out_fp = r'E:\disbr007\umn\ms\selection\footprints\ovlp\aoi1_fps.shp'
