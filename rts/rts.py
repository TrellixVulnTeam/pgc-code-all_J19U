import argparse
from datetime import datetime, timedelta
import json
import numpy as np
import os
from pathlib import Path
import platform
import subprocess
from subprocess import PIPE
import sys

from tqdm import tqdm
import geopandas as gpd
import pandas as pd

from archive_analysis.archive_analysis_utils import grid_aoi
from misc_utils.logging_utils import create_logger, create_logfile_path
from misc_utils.gpd_utils import write_gdf
from misc_utils.gdal_tools import rasterize_shp2raster_extent
from misc_utils.raster_clip import clip_rasters
from misc_utils.rio_utils import fill_internal_nodata
from dem_utils.dem_derivatives import gdal_dem_derivative
from dem_utils.dem_utils import difference_dems
from dem_utils.wbt_med import wbt_med
from dem_utils.wbt_curvature import wbt_curvature
from dem_utils.wbt_sar import wbt_sar


sys.path.append(Path(__file__).parent / "obia_utils")
from obia_utils.otb_lsms import otb_lsms
# from obia_utils.otb_grm import otb_grm, create_outname
import obia_utils.otb_grm as otb_grm
import obia_utils.otb_edge_extraction as otb_ee
# from obia_utils.otb_edge_extraction import otb_edge_extraction
from obia_utils.cleanup_objects import cleanup_objects
from obia_utils.calc_zonal_stats import calc_zonal_stats
from obia_utils.ImageObjects import ImageObjects

from classify_rts import classify_rts, grow_rts_candidates, grow_rts_simple

# TODO:
#  Standardize naming - make functions:
#   -seg_name() (exists)
#   -clean_name()
#   -zonal_stats_name()
# %%
logger = create_logger(__name__, 'sh', 'INFO')

# External py scripts
PANSH_PY = r'C:\code\imagery_utils\pgc_pansharpen.py'
NDVI_PY = r'C:\code\imagery_utils\pgc_ndvi.py'

# Config keys
seg = 'seg'
alg = 'algorithm'
params = 'params'
cleanup = 'cleanup'
out_objects = 'out_objects'
out_dir = 'out_dir'
mask_on = 'mask_on'
zonal_stats = 'zonal_stats'
zs_stats = 'stats'
zs_rasters = 'rasters'
x_space = 'x_space'
y_space = 'y_space'
grow = 'grow'
buffer = 'buffer'
DEM_DERIV = 'dem_deriv'
MED = 'med'
CURV = 'curv'
IMG_DERIV = 'img_deriv'
EDGE_EX = 'edge'

# Config values
grm = 'grm'

# Bitdepth naming convention
bitdepth_lut = {'UInt16': 'u16'}

# Strings
img_k = 'img'
ndvi_k = 'ndvi'
dem_k = 'dem'
dem_prev_k = 'dem_prev'
edge_k = 'edge'
med_k = 'med'
curv_k = 'curv'
slope_k = 'slope'
rugged_k = 'ruggedness'
sar_k = 'sar'
diff_k = 'diff'
classification_k = 'classification'
hw_class_out_k = 'headwall_class_out'
hw_class_out_cent_k = 'headwall_class_out_centroid'
rts_predis_out_k = 'rts_predis_out'
rts_class_out_k = 'rts_class_out'
out_vec_fmt_k = 'OUT_VEC_FMT'

class_fld = 'class'
rts_candidate = 'rts_candidate'

# Skip steps
pan = 'pan'
ndvi = 'ndvi'
dem_deriv = 'dem_deriv'
clip_step = 'clip_step'
edge_extraction = 'edge_extraction'
hw_seg = 'hw_seg'
hw_clean = 'hw_clean'
hw_zs = 'hw_zs'
hw_class = 'hw_class'
rts_seg = 'rts_seg'
rts_clean = 'rts_clean'
rts_zs = 'rts_zs'
rts_class = 'rts_class'
grow_seg = 'grow_seg'
grow_clean = 'grow_clean'
grow_zs = 'grow_zs'

# Constants
clip_sfx = '_clip'
clean_sfx = '_cln'


def get_config(config_file, param=None):
    config_params = json.load(open(config_file))
    if param is not None:
        try:
            config = config_params[param]
        except KeyError:
            print('Config parameter not found: {}'.format(param))
            print('Available configs:\n{}'.format('\n'.join(config.keys())))
    else:
        config = config_params

    return config


def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):
        logger.info('(subprocess) {}'.format(line.decode()))
    proc_err = ""
    for line in iter(proc.stderr.readline, b''):
        proc_err += line.decode()
    if proc_err:
        logger.info('(subprocess) {}'.format(proc_err))
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))


def main(image, dem, dem_prev, project_dir, config,
         skip_steps=None, ):
    # Convert to path objects
    image = Path(image)
    dem = Path(dem)
    dem_prev = Path(dem_prev)

    # %% Get configuration settings
    config = get_config(config_file=config)

    # Project config settings
    project_config = config['project']
    EPSG = project_config['EPSG']
    aoi = Path(project_config['AOI'])
    fill_nodata = project_config['fill_nodata']

   # Headwall and RTS config settings
    hw_config = config['headwall']
    rts_config = config['rts']
    grow_config = config['grow']

    # Preprocessing
    pansh_config = config['pansharpen']
    BITDEPTH = pansh_config['t']
    STRETCH = pansh_config['c']

    dem_deriv_config = config[DEM_DERIV]
    med_config = dem_deriv_config[MED]
    curv_config = dem_deriv_config[CURV]
    img_deriv_config = config[IMG_DERIV]
    edge_config = img_deriv_config[EDGE_EX]

    # %% Build project directory structure
    logger.info('Creating project directory structure...')
    project_dir = Path(project_dir)
    if not project_dir.exists():
        logger.info('Creating project parent directory: '
                    '{}'.format(project_dir))
        os.makedirs(project_dir)
    SCRATCH_DIR = project_dir / 'scratch'
    IMG_DIR = project_dir / 'img'
    PANSH_DIR = project_dir / 'pansh'
    NDVI_DIR = project_dir / 'ndvi'
    DEM_DIR = project_dir / 'dem'
    DEM_PREV_DIR = project_dir / dem_prev_k
    DEM_DERIV_DIR = DEM_DIR / 'deriv'
    SEG_DIR = project_dir / 'seg'
    HW_DIR = SEG_DIR / 'headwall'
    RTS_DIR = SEG_DIR / 'rts'
    GROW_DIR = SEG_DIR / 'grow'
    CLASS_DIR = project_dir / 'classified'
    for d in [SCRATCH_DIR, IMG_DIR, PANSH_DIR, NDVI_DIR, DEM_DIR, DEM_PREV_DIR,
              DEM_DERIV_DIR, SEG_DIR, HW_DIR, RTS_DIR, GROW_DIR, CLASS_DIR]:
        if not d.exists():
            os.makedirs(d)

    out_vec_fmt = project_config[out_vec_fmt_k]

    # %% Imagery Preprocessing
    # Pansharpen
    if pan not in skip_steps:
        logger.info('Pansharpening: {}'.format(image.name))
        pansh_cmd = '{} {} {} -p {} -d {} -t {} -c {} ' \
                    '--skip-dem-overlap-check'.format(PANSH_PY,
                                                      image,
                                                      PANSH_DIR,
                                                      EPSG,
                                                      dem,
                                                      BITDEPTH,
                                                      STRETCH)
        run_subprocess(pansh_cmd)
    # Determine output name
    pansh_img = PANSH_DIR / '{}_{}{}{}_pansh.tif'.format(image.stem,
                                                         bitdepth_lut[
                                                             BITDEPTH],
                                                         STRETCH,
                                                         EPSG)

    # NDVI
    if ndvi not in skip_steps:
        logger.info('Creating NDVI from: {}'.format(pansh_img.name))
        ndvi_cmd = '{} {}'.format(NDVI_PY, pansh_img, NDVI_DIR)
        run_subprocess(ndvi_cmd)
    # Determine NDVI name
    ndvi_img = NDVI_DIR / '{}_ndvi.tif'.format(pansh_img.stem)
    # ndvi_img = NDVI_DIR / '{}_ndvi.tif'.format(image.stem)

    # %% Clip to AOI
    # Organize inputs
    inputs = {img_k: pansh_img,
              ndvi_k: ndvi_img,
              dem_k: dem,
              dem_prev_k: dem_prev, }

    if aoi:
        logger.info('Clipping inputs to AOI...')
        for k, r in tqdm(inputs.items()):
            # out_path = r.parent / '{}{}{}'.format(r.stem, clip_sfx,
            #                                       r.suffix)
            out_path = project_dir / k / '{}{}{}'.format(r.stem,
                                                         clip_sfx,
                                                         r.suffix)
            if clip_step not in skip_steps:
                logger.debug(
                    'Clipping input {} to AOI: {}'.format(k, aoi.name))
                clip_rasters(str(aoi), str(r), out_path=str(out_path),
                             out_suffix='')
            inputs[k] = out_path
    if fill_nodata:
        logger.info('Filling internal NoData gaps in sources...')
        for k, r in tqdm(inputs.items()):
            # Only fill image no data
            if k in [img_k, ndvi_k]:
                filled = inputs[k].parent / '{}_filled{}'.format(inputs[k].stem,
                                                                 inputs[k].suffix)
                fill_internal_nodata(inputs[k], filled, aoi)
                inputs[k] = filled

    # %% EdgeExtraction
    edge_config[img_k] = inputs[img_k]
    edge_config[out_dir] = IMG_DIR
    edge = otb_ee.create_outname(**edge_config)
    if edge_extraction not in skip_steps:
        logger.info('Creating EdgeExtraction')
        otb_ee.otb_edge_extraction(**edge_config)
    inputs[edge_k] = edge

    # %% DEM Derivatives
    if dem_deriv not in skip_steps:
        # DEM Diff
        logger.info('Creating DEM Difference...')
        diff = DEM_DERIV_DIR / 'dem_diff.tif'
        difference_dems(str(inputs[dem_k]), str(inputs[dem_prev_k]),
                        out_dem=str(diff))

        # Slope
        logger.info('Creating slope...')
        slope = DEM_DERIV_DIR / '{}_slope{}'.format(dem.stem, dem.suffix)
        gdal_dem_derivative(str(inputs[dem_k]), str(slope), 'slope')
        # Ruggedness
        logger.info('Creating ruggedness index...')
        ruggedness = DEM_DERIV_DIR / '{}_rugged{}'.format(dem.stem, dem.suffix)
        gdal_dem_derivative(str(inputs[dem_k]), str(ruggedness), 'TRI')

        # MED
        logger.info('Creating Maximum Elevation Deviation...')
        med = wbt_med(str(inputs[dem_k]), out_dir=str(DEM_DERIV_DIR),
                      **med_config)

        # Curvature
        logger.info('Creating profile curvature...')
        curvature = wbt_curvature(str(inputs[dem_k]),
                                  out_dir=str(DEM_DERIV_DIR),
                                  **curv_config)

        # Surface Area Ratio
        logger.info('Creating Surface Area Ratio...')
        sar = wbt_sar(str(inputs[dem_k]), out_dir=str(DEM_DERIV_DIR))

        inputs[med_k] = med
        inputs[curv_k] = curvature
        inputs[slope_k] = slope
        inputs[rugged_k] = ruggedness
        inputs[diff_k] = diff
        inputs[sar_k] = sar

    # %% SEGMENTATION PREPROCESSING - Segment, calculate zonal statistics
    # %%
    # HEADWALL
    # Segmentation
    hw_config[seg][params][img_k] = inputs[img_k]
    hw_config[seg][params][out_dir] = HW_DIR
    if hw_config[seg][alg] == grm:
        logger.info('Segmenting subobjects (headwalls)...')
        if hw_seg not in skip_steps:
            hw_objects = otb_grm.otb_grm(**hw_config[seg][params])
        else:
            hw_objects = otb_grm.create_outname(**hw_config[seg][params],
                                                name_only=True)
            logger.debug('Using provided headwall segmentation: '
                         '{}'.format(Path(hw_objects).relative_to(project_dir)))

    # %% Cleanup
    # Create path to write cleaned objects to
    hw_objects = Path(hw_objects)
    cleaned_objects_out = str(hw_objects.parent / '{}{}{}'.format(
        hw_objects.stem, clean_sfx, hw_objects.suffix))

    if hw_clean not in skip_steps:
        if hw_config[cleanup][cleanup]:
            logger.info('Cleaning up subobjects...')
            cleanup_params = hw_config[cleanup][params]
            cleanup_params[mask_on] = str(inputs[dem_k])
            # hw_objects = Path(hw_objects)
            hw_objects = cleanup_objects(input_objects=str(hw_objects),
                                         out_objects=cleaned_objects_out,
                                         **cleanup_params)
    else:
        logger.debug('Using provided cleaned headwall objects'
                    '{}: '.format(Path(cleaned_objects_out).relative_to(project_dir)))
        hw_objects = cleaned_objects_out

    # %% Zonal Stats
    logger.info('Calculating zonal statistics on headwall objects...')
    hw_objects_path = Path(hw_objects)
    hw_zs_out_path = '{}_zs{}'.format(
        hw_objects_path.parent / hw_objects_path.stem, hw_objects_path.suffix)
    if hw_zs not in skip_steps:

        # Calculate zonal stats
        zonal_stats_inputs = {k: {'path': v,
                                  'stats': hw_config[zonal_stats][zs_stats]}
                              for k, v in inputs.items()
                              if k in hw_config[zonal_stats][zs_rasters]}
        hw_objects = calc_zonal_stats(shp=hw_objects,
                                      rasters=zonal_stats_inputs,
                                      out_path=hw_zs_out_path, )
    else:
        logger.debug('Using provided headwall objects with zonal stats: '
                    '{}'.format(Path(hw_zs_out_path).relative_to(project_dir)))
        hw_objects = hw_zs_out_path

    # %%
    # RTS
    # Naming
    rts_config[seg][params][img_k] = inputs[img_k]
    rts_config[seg][params][out_dir] = RTS_DIR
    # Segmentation
    if rts_config[seg][alg] == grm:
        logger.info('Segmenting superobjects (RTS)...')
        if rts_seg not in skip_steps:
            rts_objects = otb_grm.otb_grm(**rts_config[seg][params])
        else:
            rts_objects = otb_grm.create_outname(**rts_config[seg][params],
                                         name_only=True)
            logger.debug('Using provided RTS seg: '
                        '{}'.format(Path(rts_objects).relative_to(project_dir)))
        rts_objects = Path(rts_objects)

    # %% Cleanup
    cleaned_objects_out = str(rts_objects.parent / '{}_cln{}'.format(
        rts_objects.stem, rts_objects.suffix))

    if rts_clean not in skip_steps:
        if rts_config[cleanup][cleanup]:
            logger.info('Cleaning up objects...')
            cleanup_params = rts_config[cleanup][params]
            cleanup_params[mask_on] = str(inputs[dem_k])
            rts_objects = Path(rts_objects)
            rts_objects = cleanup_objects(input_objects=rts_objects,
                                          out_objects=cleaned_objects_out,
                                          **cleanup_params)
    else:
        logger.debug('Using provided cleaned RTS objects: '
                     '{}'.format(Path(cleaned_objects_out).relative_to(project_dir)))
        rts_objects = cleaned_objects_out

    # %% Zonal Stats
    logger.info('Calculating zonal statistics on super objects...')
    rts_objects_path = Path(rts_objects)
    rts_zs_out_path = '{}_zs{}'.format(rts_objects_path.parent /
                                       rts_objects_path.stem,
                                       rts_objects_path.suffix)
    if rts_zs not in skip_steps:
        # Calculate zonal_stats
        zonal_stats_inputs = {k: {'path': v,
                                  'stats': rts_config[zonal_stats][zs_stats]}
                              for k, v in inputs.items()
                              if k in rts_config[zonal_stats][zs_rasters]}
        rts_objects = calc_zonal_stats(shp=rts_objects,
                                       rasters=zonal_stats_inputs,
                                       out_path=rts_zs_out_path, )
    else:
        logger.debug('Using provided RTS zonal stats objects: '
                    '{}'.format(Path(rts_zs_out_path).relative_to(project_dir)))
        rts_objects = rts_zs_out_path

    # %% CLASSIFICATION
    if hw_config[classification_k][hw_class_out_k]:
        hw_class_out = CLASS_DIR / '{}{}'.format(hw_class_out_k, out_vec_fmt)
    if hw_config[classification_k][hw_class_out_cent_k]:
        hw_class_out_centroid = CLASS_DIR / '{}_cent{}'.format(hw_class_out_k,
                                                               out_vec_fmt)

    # Pass path to classified headwall objects if using previously classified
    if hw_class in skip_steps:
        hw_candidates_in = hw_class_out
    else:
        hw_candidates_in = None

    if rts_config[classification_k][rts_predis_out_k]:
        rts_predis_out = CLASS_DIR / '{}{}'.format(rts_predis_out_k, out_vec_fmt)
    if rts_config[classification_k][rts_class_out_k]:
        rts_class_out = CLASS_DIR / '{}{}'.format(rts_class_out_k, out_vec_fmt)

    if rts_class not in skip_steps:
        logger.info('Classifying RTS...')
        rts_objects = classify_rts(
                        sub_objects_path=hw_objects,
                        super_objects_path=rts_objects,
                        headwall_candidates_out=hw_class_out,
                        headwall_candidates_centroid_out=hw_class_out_centroid,
                        rts_predis_out=rts_predis_out,
                        rts_candidates_out=rts_class_out,
                        aoi_path=None,
                        headwall_candidates_in=hw_candidates_in,
                        aoi=aoi)
    else:
        logger.debug('Using provided classified RTS objects: '
                    '{}'.format(Path(rts_class_out).relative_to(project_dir)))
        rts_objects = rts_class_out

    #%% GROW OBJECTS
    logger.info('Creating grow subobjects..')
    # Segment AOI into simple grow
    grow_config[seg][params][img_k] = inputs[img_k]
    grow_config[seg][params][out_dir] = GROW_DIR

    if grow_seg not in skip_steps:
        # grow = grid_aoi(aoi, x_space=grow_config[seg][x_space],
        #                       y_space=grow_config[seg][y_space], poly=True)
        # if grow_out:
        #     logger.info('Writing grow segmentation to: '
        #                 '{}'.format(grow_out))
        #     write_gdf(grow, grow_out)
        grow = otb_grm.otb_grm(**grow_config[seg][params])
    else:
        grow = otb_grm.create_outname(**grow_config[seg][params], name_only=True)
        logger.debug('Using provided grow objects: '
                     '{}'.format(Path(grow).relative_to(project_dir)))

    # Cleanup
    grow = Path(grow)
    cleaned_grow = str(grow.parent / '{}_cln{}'.format(grow.stem, grow.suffix))
    if grow_clean not in skip_steps:
        if grow_config[cleanup][cleanup]:
            logger.info('Cleaning up objects...')
            cleanup_params = grow_config[cleanup][params]
            cleanup_params[mask_on] = str(inputs[dem_k])
            cleaned_grow = cleanup_objects(input_objects=str(grow),
                                           out_objects=cleaned_grow,
                                           **cleanup_params)

    cleaned_grow = Path(cleaned_grow)
    grow_zs_out_path = cleaned_grow.parent / '{}_zs{}'.format(cleaned_grow.stem,
                                                              cleaned_grow.suffix)
    if grow_zs not in skip_steps:
        logger.info('Merging RTS candidates into grow objects...')
        # Load small objects
        so = gpd.read_file(cleaned_grow)

        # Burn rts in, including class name
        r = gpd.read_file(rts_objects)
        r = r[r[class_fld] == rts_candidate][[class_fld, r.geometry.name]]

        # Erase subobjects under RTS candidates
        diff = gpd.overlay(so, r, how='difference')
        # Merge RTS candidates back in
        merged = pd.concat([diff, r])
        merged_out = SEG_DIR / GROW_DIR / 'merged.shp'
        write_gdf(merged, merged_out)
        # merged.to_file(merged_out)

        # Zonal Stats
        zonal_stats_inputs = {k: {'path': v,
                                  'stats': grow_config[zonal_stats][zs_stats]}
                              for k, v in inputs.items()
                              if k in grow_config[zonal_stats][zs_rasters]}

        logger.info('Calculating zonal statistics on grow objects...')
        logger.debug('Computing zonal statistics on: '
                     '{}'.format(zonal_stats_inputs.keys()))
        grow = calc_zonal_stats(shp=merged_out,
                                rasters=zonal_stats_inputs,
                                out_path=str(grow_zs_out_path))

    # Do growing
    logger.info('Growing RTS objects into subobjects...')

    # Grow from rts
    # grow_objects = ImageObjects(grow_zs_out_path,
    #                             value_fields=zonal_stats_inputs)
    # # TODO: Remove after converting to use gpkg. This is just because of the
    # #  shapefile field size limit
    # grow_objects.objects.rename(columns={'ruggedness': 'ruggedness_mean'},
    #                             inplace=True)
    #
    # rts_objects = ImageObjects(rts_objects)
    # grown = grow_rts_candidates(rts_objects, grow_objects)

    grown, grow_candidates = grow_rts_simple(grow_zs_out_path)

    logger.info('Writing grow objects to file: {}'.format(CLASS_DIR / 'grow_candidates.shp'))
    write_gdf(grow_candidates, CLASS_DIR / 'grow_candidates.shp')

    # n = datetime.now().strftime('%Y%b%d_%H%M%S').lower()

    rts_classified = CLASS_DIR / 'RTS.shp'
    logger.info('Writing classfied RTS features: {}'.format(rts_classified))
    write_gdf(grown, rts_classified)

    logger.info('Done')


if __name__ == '__main__':
    # Default arguments and choices
    ARGDEF_SKIP_CHOICES = [pan, ndvi, dem_deriv, edge_extraction, clip_step,
                           hw_seg, hw_clean, hw_zs, hw_class,
                           rts_seg, rts_clean, rts_zs, rts_class,
                           grow_seg, grow_clean, grow_zs]

    parser = argparse.ArgumentParser()

    # Inputs
    parser.add_argument('-img', '--image_input', type=os.path.abspath,
                        help='The path to the multispectral image to use.')
    parser.add_argument('-dem', '--dem_input', type=os.path.abspath,
                        help='The path to the DEM corresponding to the input '
                             'image.')
    parser.add_argument('-prev_dem', '--previous_dem', type=os.path.abspath,
                        help='The path to a DEM from a previous year to use '
                             'to compute change metrics.')
    parser.add_argument('-pd', '--project_dir', type=os.path.abspath,
                        help='Path to directory underwhich to create project '
                             'files.')
    parser.add_argument('-aoi', type=os.path.abspath,
                        help='Path to AOI to restrict analysis to.')
    parser.add_argument('--config', type=os.path.abspath,
                        help='Path to json config file to use.')
    parser.add_argument('--skip_steps', nargs='+',
                        choices=ARGDEF_SKIP_CHOICES,
                        help='Skip these steps, paths to intermediate layers '
                             'must exist as computed by previous steps.')
    parser.add_argument('--logdir', type=os.path.abspath)

    # prj_dir = r'E:\disbr007\umn\2020sep27_eureka'
    # # psd = 'rts_test2021jan18'
    # psd = 'rts_test2021feb06'
    # os.chdir(prj_dir)
    # sys.argv = [r'C:\code\pgc-code-all\rts\rts.py',
    #             '-img', r'img\ortho_WV02_20140703\WV02_20140703013631_'
    #                     r'1030010032B54F00_14JUL03013631-M1BS-'
    #                     r'500287602150_01_P009.tif',
    #             '-dem', r'dems\sel\WV02_20140703_1030010033A84300_'
    #                     r'1030010032B54F00\WV02_20140703_1030010033A84300_'
    #                     r'1030010032B54F00_2m_lsf_seg1_dem_masked.tif',
    #             '-prev_dem', r'dems\sel\WV02_20110811_103001000D198300_'
    #                          r'103001000C5D4600_pca'
    #                          r'\WV02_20110811_103001000D198300_103001000C5D4600_'
    #                          r'2m_lsf_seg1_dem_masked_pca-DEM.tif',
    #             '-pd', psd,
    #             '-aoi', r'aois\test_aoi.shp',
    #             '--skip_steps',
    #             pan,
    #             ndvi,
    #             hw_seg,
    #             hw_clean,
    #             hw_zs,
    #             # hw_class,
    #             rts_seg,
    #             rts_clean,
    #             rts_zs,
    #             # rts_class,
    #             grow_seg,
    #             grow_clean,
    #             grow_zs,
    #             '--config',
    #             r'E:\disbr007\umn\2020sep27_eureka\rts_test2021jan18\config.json',
    #             '--logdir', os.path.join(prj_dir, psd, 'logs'),
    #             ]

    prj_dir = r'E:\disbr007\umn\accuracy_assessment'
    psd = 'test_aoi2_mr_pansh_2021feb15'
    os.chdir(prj_dir)
    sys.argv = [r'C:\code\pgc-code-all\rts\rts.py',
                '-img', r'E:\disbr007\umn\2020sep27_eureka\img\ortho_WV02_20140809'
                        r'\WV02_20140809235614_10300100348BE800_14AUG09235614-M1BS-'
                        r'500281124060_01_P001.tif',
                # '-img', r'E:\disbr007\umn\2020sep27_eureka\img\ortho_WV02_20140809_mr'
                #         r'\WV02_20140809235614_10300100348BE800_14AUG09235614-M1BS-'
                #         r'500281124060_01_P001_u16mr3413.tif',
                '-dem', r'E:\disbr007\umn\2020sep27_eureka\dems\all'
                        r'\WV02_20140809_10300100348BE800_103001003542D300'
                        r'\WV02_20140809_10300100348BE800_103001003542D300_2m_lsf_seg2_dem_masked.tif',
                '-prev_dem', r'E:\disbr007\umn\2020sep27_eureka\dems\sel'
                             r'\WV02_20110811_103001000D198300_103001000C5D4600_pca_WV02_20140809'
                             r'\WV02_20110811_103001000D198300_103001000C5D4600_2m_lsf_seg1_dem_masked_pca-DEM.tif',
                '-pd', psd,
                '-aoi', r'aois\test_aoi2.shp',
                '--skip_steps',
                pan,
                ndvi,
                # hw_seg,
                # hw_clean,
                # hw_zs,
                # hw_class,
                # rts_seg,
                # rts_clean,
                # rts_zs,
                # rts_class,
                # grow_seg,
                # grow_clean,
                # grow_zs,
                # '--config',
                # r'E:\disbr007\umn\accuracy_assessment\test_aoi2_mr\config.json',
                '--logdir', os.path.join(prj_dir, psd, 'logs'),
                ]

    # mj_ward1_n
    # prj_dir = r'E:\disbr007\umn\accuracy_assessment'
    # psd = 'mj_ward_n_2014_2011'
    # os.chdir(prj_dir)
    # sys.argv = [r'C:\code\pgc-code-all\rts\rts.py',
    #             '-img', r'E:\disbr007\umn\2020sep27_eureka\img\ortho_WV02_20140809'
    #                     r'\WV02_20140809235614_10300100348BE800_14AUG09235614-M1BS-'
    #                     r'500281124060_01_P001.tif',
    #             '-dem', r'E:\disbr007\umn\2020sep27_eureka\dems\all'
    #                     r'\WV02_20140809_10300100348BE800_103001003542D300'
    #                     r'\WV02_20140809_10300100348BE800_103001003542D300_2m_lsf_seg2_dem_masked.tif',
    #             '-prev_dem', r'E:\disbr007\umn\accuracy_assessment\mj_ward1\data\dems'
    #                          r'\mj_ward1_n_2014_2011'
    #                          r'\WV02_20110811_103001000D198300_103001000C5D4600_2m_lsf_seg1_dem_masked_pca-DEM.tif',
    #             '-pd', psd,
    #             '-aoi', r'aois\mj_ward_n.shp',
    #             '--skip_steps',
    #             pan,
    #             ndvi,
    #             hw_seg,
    #             hw_clean,
    #             hw_zs,
    #             # hw_class,
    #             rts_seg,
    #             rts_clean,
    #             rts_zs,
    #             # rts_class,
    #             grow_seg,
    #             grow_clean,
    #             # grow_zs,
    #             '--logdir', os.path.join(prj_dir, psd, 'logs'),
    #             ]


    args = parser.parse_args()

    image = args.image_input
    dem = args.dem_input
    dem_prev = args.previous_dem
    project_dir = args.project_dir
    # aoi = args.aoi
    config = args.config
    skip_steps = args.skip_steps
    logdir = args.logdir

    if logdir:
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logger = create_logger('obia_utils.cleanup_objects', 'fh', 'INFO',
                               create_logfile_path(Path(__file__).name,
                                                   logdir))
        logger = create_logger('obia_utils.otb_grm', 'fh', 'INFO',
                               create_logfile_path(Path(__file__).name,
                                                   logdir))
        logger = create_logger('obia_utils.ImageObjects', 'fh', 'INFO',
                               create_logfile_path(Path(__file__).name,
                                                   logdir))
        logger = create_logger('classify_rts', 'fh', 'DEBUG',
                               create_logfile_path(Path(__file__).name,
                                                   logdir)
                               )
        logger = create_logger(__name__, 'fh', 'DEBUG',
                               create_logfile_path(Path(__file__).name,
                                                   logdir))

    if not config:
        config = Path(project_dir) / 'config.json'

    logger.info('Beginning Retrogressive Thaw Slump OBIA Classification.')
    logger.info('Project directory: {}'.format(project_dir))

    start = datetime.now()
    main(image=image,
         dem=dem,
         dem_prev=dem_prev,
         project_dir=project_dir,
         # aoi=aoi,
         config=config,
         skip_steps=skip_steps)
    end = datetime.now()

    runtime = end - start
    runtime = divmod(runtime.total_seconds(), 60)
    logger.info('Runtime: {}'.format(str(runtime)))
