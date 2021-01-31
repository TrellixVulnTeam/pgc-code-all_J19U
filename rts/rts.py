import argparse
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

from archive_analysis.archive_analysis_utils import grid_aoi
from misc_utils.logging_utils import create_logger, create_logfile_path
from misc_utils.gpd_utils import write_gdf
from misc_utils.gdal_tools import rasterize_shp2raster_extent
from misc_utils.raster_clip import clip_rasters
from dem_utils.dem_derivatives import gdal_dem_derivative
from dem_utils.dem_utils import difference_dems
from dem_utils.wbt_med import wbt_med
from dem_utils.wbt_curvature import wbt_curvature
from dem_utils.wbt_sar import wbt_sar

sys.path.append(Path(__file__).parent / "obia_utils")
from obia_utils.otb_lsms import otb_lsms
from obia_utils.otb_grm import otb_grm, create_outname
from obia_utils.cleanup_objects import cleanup_objects
from obia_utils.calc_zonal_stats import calc_zonal_stats
from obia_utils.ImageObjects import ImageObjects

from classify_rts import classify_rts, grow_rts_candidates

# TODO:
#  Standardize naming - make functions:
#   -seg_name() (exists)
#   -clean_name()
#   -zonal_stats_name()
# %%
logger = create_logger(__name__, 'sh', 'INFO')

# CONFIG_FILE = Path(__file__).parent / 'config.json'

# External py scripts
pansh_py = r'C:\code\imagery_utils\pgc_pansharpen.py'
ndvi_py = r'C:\code\imagery_utils\pgc_ndvi.py'

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

# Config values
grm = 'grm'

# Bitdepth naming convention
bitdepth_lut = {'UInt16': 'u16'}

# Strings
img_k = 'img'
ndvi_k = 'ndvi'
dem_k = 'dem'
dem_prev_k = 'dem_prev'
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

   # Headwall and RTS config settings
    hw_config = config['headwall']
    rts_config = config['rts']
    grow_config = config['grow']

    # Preprocessing
    pansh_config = config['pansharpen']
    BITDEPTH = pansh_config['t']
    STRETCH = pansh_config['c']

    dem_deriv_config = config['dem_deriv']
    med_config = dem_deriv_config['med']
    curv_config = dem_deriv_config['curv']

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
    DEM_DERIV_DIR = DEM_DIR / 'deriv'
    SEG_DIR = project_dir / 'seg'
    HW_DIR = SEG_DIR / 'headwall'
    RTS_DIR = SEG_DIR / 'rts'
    GROW_DIR = SEG_DIR / 'grow'
    CLASS_DIR = project_dir / 'classified'
    for d in [SCRATCH_DIR, IMG_DIR, PANSH_DIR, NDVI_DIR, DEM_DIR,
              DEM_DERIV_DIR, SEG_DIR, HW_DIR, RTS_DIR, GROW_DIR, CLASS_DIR]:
        if not d.exists():
            os.makedirs(d)

    out_vec_fmt = project_config[out_vec_fmt_k]

    # %% Imagery Preprocessing
    # Pansharpen
    if pan not in skip_steps:
        logger.info('Pansharpening: {}'.format(image.name))
        pansh_cmd = '{} {} -p {} -d {} -t {} -c {} ' \
                    '--skip-dem-overlap-check'.format(image,
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
        ndvi_cmd = '{} {}'.format(ndvi_py, pansh_img, NDVI_DIR)
        run_subprocess(ndvi_cmd)
    # Determine NDVI name
    ndvi_img = NDVI_DIR / '{}_ndvi.tif'.format(pansh_img.stem)

    # %% Clip to AOI
    # Organize inputs
    inputs = {img_k: pansh_img,
              ndvi_k: ndvi_img,
              dem_k: dem,
              dem_prev_k: dem_prev, }

    if aoi:
        logger.info('Clipping inputs to AOI...')
        for k, r in tqdm(inputs.items()):
            out_path = r.parent / '{}{}{}'.format(r.stem, clip_sfx,
                                                  r.suffix)
            if clip_step not in skip_steps:
                logger.debug(
                    'Clipping input {} to AOI: {}'.format(k, aoi.name))
                clip_rasters(str(aoi), str(r), out_path=str(out_path),
                             out_suffix='')
            inputs[k] = out_path

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
            hw_objects = otb_grm(**hw_config[seg][params])
        else:
            hw_objects = create_outname(**hw_config[seg][params],
                                        name_only=True)
            logger.debug('Using provided headwall segmentation:'
                        '\n\t{}'.format(hw_objects))

    # %% Cleanup
    # Create path to write cleaned objects to
    hw_objects = Path(hw_objects)
    cleaned_objects_out = str(hw_objects.parent / '{}{}{}'.format(
        hw_objects.stem, clean_sfx, hw_objects.suffix))

    if hw_clean not in skip_steps:
        if hw_config[cleanup][cleanup]:
            logger.info('Cleaning up subobjects...')
            cleanup_params = hw_config[cleanup][params]
            # hw_objects = Path(hw_objects)
            hw_objects = cleanup_objects(input_objects=str(hw_objects),
                                         out_objects=cleaned_objects_out,
                                         **cleanup_params)
    else:
        logger.debug('Using provided cleaned headwall objects'
                    '\n\t{}'.format(cleaned_objects_out))
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
        logger.debug('Using provided headwall objects with zonal stats'
                    '\n\t{}'.format(hw_zs_out_path))
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
            rts_objects = otb_grm(**rts_config[seg][params])
        else:
            rts_objects = create_outname(**rts_config[seg][params],
                                         name_only=True)
            logger.debug('Using provided RTS seg:'
                        '\n\t{}'.format(rts_objects))
        rts_objects = Path(rts_objects)

    # %% Cleanup
    cleaned_objects_out = str(rts_objects.parent / '{}_cln{}'.format(
        rts_objects.stem, rts_objects.suffix))

    if rts_clean not in skip_steps:
        if rts_config[cleanup][cleanup]:
            logger.info('Cleaning up objects...')
            cleanup_params = rts_config[cleanup][params]
            rts_objects = Path(rts_objects)

            rts_objects = cleanup_objects(input_objects=rts_objects,
                                          out_objects=cleaned_objects_out,
                                          **cleanup_params)
    else:
        logger.debug('Using provided cleaned RTS objects'
                    '\n\t{}'.format(cleaned_objects_out))
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
        logger.debug('Using provided RTS zonal stats objects'
                    '\n\t{}'.format(rts_zs_out_path))
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
        logger.debug('Using provided classified RTS objects'
                    '\n\t{}'.format(rts_class_out))
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
        grow = otb_grm(**grow_config[seg][params])
    else:
        grow = create_outname(**grow_config[seg][params], name_only=True)
        logger.debug('Using provided grow objects'
                     '\n\t{}'.format(grow))

    # Cleanup
    grow = Path(grow)
    cleaned_grow = str(grow.parent / '{}_cln{}'.format(grow.stem, grow.suffix))
    if grow_clean not in skip_steps:
        if grow_config[cleanup][cleanup]:
            logger.info('Cleaning up objects...')
            cleanup_params = grow_config[cleanup][params]
            cleaned_grow = cleanup_objects(input_objects=str(grow),
                                           out_objects=cleaned_grow,
                                           **cleanup_params)
        # # Rasterize candidates to use as mask
        # # Load objects
        # rts_objects_area = gpd.read_file(rts_objects)
        # rts_objects_area = rts_objects_area[rts_objects_area[class_fld]==rts_candidate]
        # rts_objects_area.geometry = rts_objects_area.geometry.buffer(
        #     grow_config[grow][buffer]
        # )
        # # Create bool column to use for masking
        # rts_bool = 'rts_bool'
        # rts_objects_area[rts_bool] = np.where(
        #     rts_objects_area[class_fld] == rts_candidate, 1, 0)
        #
        # rts_objects_area_temp = r'/vsimem/rts_objects_area_temp.shp'
        # rts_objects_area.to_file(rts_objects_area_temp)
        #
        # rts_candidate_mask = RTS_DIR / "rasterized_mask.tif"
        # rasterize_shp2raster_extent(rts_objects_area_temp,
        #                             grow_config[cleanup][params][mask_on],
        #                             attribute=rts_bool,
        #                             write_rasterized=True,
        #                             out_path=str(rts_candidate_mask),
        #                             nodata_val=0)
        # grow = cleanup_objects(input_objects=str(grow_out),
        #                        out_objects=str(cleaned_grow),
        #                        mask_on=str(rts_candidate_mask),
        #                        overwrite=True)

    # Zonal Stats
    cleaned_grow = Path(cleaned_grow)
    grow_zs_out_path = cleaned_grow.parent / '{}_zs{}'.format(cleaned_grow.stem,
                                                            cleaned_grow.suffix)
    zonal_stats_inputs = {k: {'path': v,
                              'stats': grow_config[zonal_stats][zs_stats]}
                          for k, v in inputs.items()
                          if k in grow_config[zonal_stats][zs_rasters]}

    if grow_zs not in skip_steps:
        logger.info('Calculating zonal statistics on grow objects...')
        logger.debug('Computing zonal statistics on: '
                     '{}'.format(zonal_stats_inputs.keys()))
        grow = calc_zonal_stats(shp=str(cleaned_grow),
                                rasters=zonal_stats_inputs,
                                out_path=str(grow_zs_out_path))

    # Do growing
    logger.info('Growing RTS objects into subobjects:\n ({})...'.format(grow_zs_out_path))
    grow_objects = ImageObjects(grow_zs_out_path,
                                value_fields=zonal_stats_inputs)
    # TODO: Remove after converting to use gpkg. This is just because of the
    #  shapefile field size limit
    grow_objects.objects.rename(columns={'ruggedness': 'ruggedness_mean'},
                                inplace=True)

    rts_objects = ImageObjects(rts_objects)
    grown = grow_rts_candidates(rts_objects, grow_objects)

    grown.write_objects(r'C:\temp\grow_pwr_2021jan31_1059.shp')

    logger.info('Done')


if __name__ == '__main__':
    # Default arguments and choices
    ARGDEF_SKIP_CHOICES = [pan, ndvi, dem_deriv, clip_step,
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

    prj_dir = r'E:\disbr007\umn\2020sep27_eureka'
    pd = 'rts_test2021jan18'
    os.chdir(prj_dir)
    sys.argv = [r'C:\code\pgc-code-all\rts\rts.py',
                '-img', r'img\ortho_WV02_20140703\WV02_20140703013631_'
                        r'1030010032B54F00_14JUL03013631-M1BS-'
                        r'500287602150_01_P009.tif',
                '-dem', r'dems\sel\WV02_20140703_1030010033A84300_'
                        r'1030010032B54F00\WV02_20140703_1030010033A84300_'
                        r'1030010032B54F00_2m_lsf_seg1_dem_masked.tif',
                '-prev_dem', r'dems\sel\WV02_20110811_103001000D198300_'
                             r'103001000C5D4600_pca'
                             r'\WV02_20110811_103001000D198300_103001000C5D4600_'
                             r'2m_lsf_seg1_dem_masked_pca-DEM.tif',
                '-pd', pd,
                '-aoi', r'aois\test_aoi.shp',
                '--skip_steps',
                pan,
                ndvi,
                hw_seg,
                hw_clean,
                hw_zs,
                hw_class,
                rts_seg,
                rts_clean,
                rts_zs,
                rts_class,
                grow_seg,
                grow_clean,
                grow_zs,
                '--config',
                r'E:\disbr007\umn\2020sep27_eureka\rts_test2021jan18\config.json',
                '--logdir', os.path.join(prj_dir, pd),
                ]

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
        logger = create_logger(__name__, 'fh', 'DEBUG',
                               create_logfile_path(Path(__file__).name,
                                                   logdir))

    main(image=image,
         dem=dem,
         dem_prev=dem_prev,
         project_dir=project_dir,
         # aoi=aoi,
         config=config,
         skip_steps=skip_steps)

# TODO: Add value fields if doing merging
# all computed zs fields plus on_border