import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
from subprocess import PIPE
import sys

from tqdm import tqdm

from misc_utils.logging_utils import create_logger
from misc_utils.raster_clip import clip_rasters
from dem_utils.dem_utils import difference_dems
from dem_utils.wbt_med import wbt_med
from dem_utils.wbt_curvature import wbt_curvature
from dem_utils.wbt_sar import wbt_sar
from dem_utils.dem_derivatives import gdal_dem_derivative

sys.path.append(Path(__file__).parent / "obia_utils")
from obia_utils.otb_lsms import otb_lsms
from obia_utils.otb_grm import otb_grm
from obia_utils.cleanup_objects import cleanup_objects
from obia_utils.calc_zonal_stats import calc_zonal_stats

from classify_rts import classify_rts


#%%
logger = create_logger(__name__, 'sh', 'INFO')

CONFIG_FILE = Path(__file__).parent / 'config.json'

# External py scripts
pansh_py = r'C:\code\imagery_utils\pgc_pansharpen.py'
ndvi_py = r'C:\code\imagery_utils\pgc_ndvi.py'

# Config keys
seg = 'seg'
alg = 'algorithm'
params = 'params'

cleanup = 'cleanup'
out_objects = 'out_objects'
mask_on = 'mask_on'

zonal_stats = "zonal_stats"

# Config values
grm = 'grm'

# Bitdepth naming convention
bitdepth_lut = {'UInt16': 'u16'}

# Strings
img_k = 'img'
dem_k = 'dem'
dem_prev_k = 'dem_prev'
med_k = 'med'
curv_k = 'curv'
slope_k = 'slope'
rugged_k = 'ruggedness'
sar_k = 'sar'
diff_k = 'diff'


def get_config(param=None, config_file=CONFIG_FILE):
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


def main(image, dem, dem_prev, project_dir,
         aoi=None,
         headwall_seg=None,
         headwall_cleaned=None,
         headwall_zonal_stats=None,
         rts_seg=None,
         rts_cleaned=None,
         rts_zonal_stats=None,
         rts_classified=None):

    # Convert to path objects
    image = Path(image)
    dem = Path(dem)
    dem_prev = Path(dem_prev)

    #%% Get configuration settings
    config = get_config()
    hw_config = config['headwall']
    rts_config = config['rts']

    project_config = config['project']
    EPSG = project_config['EPSG']

    pansh_config = config['pansharpen']
    BITDEPTH = pansh_config['t']
    STRETCH = pansh_config['c']

    dem_deriv_config = config['dem_deriv']
    med_config = dem_deriv_config['med']
    curv_config = dem_deriv_config['curv']

    #%% Build project directory structure
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
    CLASS_DIR = project_dir / 'classified'
    for d in [SCRATCH_DIR, IMG_DIR, PANSH_DIR, NDVI_DIR, DEM_DIR, SEG_DIR,
              HW_DIR, RTS_DIR, CLASS_DIR]:
        if not d.exists():
            os.makedirs(d)

    #%% Imagery Preprocessing
    # Pansharpen
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
                                                         bitdepth_lut[BITDEPTH],
                                                         STRETCH,
                                                         EPSG)
    
    # NDVI
    logger.info('Creating NDVI from: {}'.format(pansh_img.name))
    ndvi_cmd = '{} {}'.format(ndvi_py, pansh_img, NDVI_DIR)
    run_subprocess(ndvi_cmd)
    ndvi_img = NDVI_DIR / '{}_ndvi.tif'.format(pansh_img.stem)

    #%% DEM Derivatives
    # MED
    logger.info('Creating Maximum Elevation Deviation...')
    med = wbt_med(dem, out_dir=DEM_DERIV_DIR, **med_config)

    # Curvature
    logger.info('Creating profile curvature...')
    curvature = wbt_curvature(dem, out_dir=DEM_DERIV_DIR, **curv_config)

    # Slope
    logger.info('Creating slope...')
    slope = DEM_DERIV_DIR / '{}_slope{}'.format(dem.stem, dem.suffix)
    gdal_dem_derivative(dem, slope, 'slope')

    logger.info('Creating ruggedness index...')
    ruggedness = DEM_DERIV_DIR / '{}_rugged{}'.format(dem.stem, dem.suffix)
    gdal_dem_derivative(dem, ruggedness, 'ruggedness')

    # Surface Area Ratio
    logger.info('Creating Surface Area Ratio...')
    sar = wbt_sar(dem, out_dir=DEM_DERIV_DIR)

    # DEM Diff
    logger.info('Creating DEM Difference...')
    diff = DEM_DERIV_DIR / 'dem_diff.tif'
    difference_dems(dem, dem_prev, out_dem=diff)

    # Organize inputs
    inputs = {img_k: pansh_img,
              dem_k: dem,
              dem_prev_k: dem_prev,
              med_k: med,
              curv_k: curvature,
              slope_k: slope,
              rugged_k: ruggedness,
              diff_k: diff}

    #%% Clip to AOI
    if aoi:
        logger.info('Clipping inputs to AOI: {}'.format(aoi.name))
        for k, r in tqdm(inputs.items()):
            out_path = r.parent / '{}_clip{}'.format(r.stem, r.suffix)
            clip_rasters(aoi, r, out_path=out_path, out_suffix='')
            inputs[k] = out_path

    # TODO: Adjust calc_zonal_stats to take dict instead of json then
    #  build dict to pass out of inputs dict
    sys.exit()

    #%% SEGMENTATION PREPROCESSING - Segment, calculate zonal statistics
    #%%
    # HEADWALL
    # Segmentation
    if not headwall_seg:
        if hw_config[seg][alg] == grm:
            logger.info('Segmenting subobjects (headwalls)...')
            hw_objects = otb_grm(**hw_config[seg][params])
    else:
        logger.info('Using provided headwall segmentation:'
                    '\n{}'.format(headwall_seg))
        hw_objects = headwall_seg

    #%% Cleanup
    if not headwall_cleaned:
        if hw_config[cleanup][cleanup]:
            logger.info('Cleaning up subojects...')
            cleanup_params = hw_config[cleanup][params]
            hw_objects = Path(hw_objects)

            # Create path to write cleaned objects to if not provided
            cleaned_objects = cleanup_params[out_objects]
            if not cleaned_objects:
                cleaned_objects = str(hw_objects.parent / '{}_cln{}'.format(
                    hw_objects.stem, hw_objects.suffix))
                cleanup_params.pop(out_objects)

            hw_objects = cleanup_objects(input_objects=hw_objects,
                                         out_objects=cleaned_objects,
                                         **cleanup_params)
    else:
        logger.info('Using provided cleaned headwall objects'
                    '\n{}'.format(headwall_cleaned))
        hw_objects = headwall_cleaned

    #%% Zonal Stats
    if not headwall_zonal_stats:
        hw_objects_path = Path(hw_objects)
        hw_zs_out_path = '{}_zs'.format(hw_objects_path.parent / hw_objects_path.stem,
                                        hw_objects_path.suffix)
        hw_objects = calc_zonal_stats(shp=hw_objects,
                                      out_path=hw_zs_out_path,
                                      **hw_config[zonal_stats][params])
    else:
        logger.info('Using provided headwall objects with zonal stats'
                    '\n{}'.format(headwall_zonal_stats))
        hw_objects = headwall_zonal_stats


    #%%
    # RTS
    # Segmentation
    if not rts_seg:
        if rts_config[seg][alg] == grm:
            logger.info('Calling segmenting superobjects (headwalls)...')
            rts_objects = otb_grm(**rts_config[seg][params])
    else:
        logger.info('Using provided RTS seg'
                    '\n{}'.format(rts_seg))
        rts_objects = rts_seg

    #%% Cleanup
    if not rts_cleaned:
        if rts_config[cleanup][cleanup]:
            logger.info('Cleaning up objects...')
            cleanup_params = rts_config[cleanup][params]
            rts_objects = Path(rts_objects)

            # Create path to write cleaned objects to if not provided
            cleaned_objects = cleanup_params[out_objects]
            if not cleaned_objects:
                cleaned_objects = str(rts_objects.parent / '{}_cln{}'.format(
                    rts_objects.stem, rts_objects.suffix))
                cleanup_params.pop(out_objects)

            rts_objects = cleanup_objects(input_objects=rts_objects,
                                          out_objects=cleaned_objects,
                                          **cleanup_params)
    else:
        logger.info('Using provided cleaned RTS objects'
                    '\n{}'.format(rts_cleaned))
        rts_objects = rts_cleaned

    #%% Zonal Stats
    if not rts_zonal_stats:
        rts_objects_path = Path(rts_objects)
        rts_zs_out_path = '{}_zs{}'.format(rts_objects_path.parent /
                                           rts_objects_path.stem,
                                           rts_objects_path.suffix)
        rts_objects = calc_zonal_stats(shp=rts_objects,
                                       out_path=rts_zs_out_path,
                                       **rts_config[zonal_stats][params])
        logger.info(rts_objects)
    else:
        logger.info('Using provided RTS zonal stats objects'
                    '\n{}'.format(rts_zonal_stats))
        rts_objects = rts_zonal_stats

    #%% CLASSIFICATION
    if not rts_classified:
        logger.info('Classifying RTS...')
        rts_objects = classify_rts(sub_objects_path=hw_objects,
                                   super_objects_path=rts_objects,
                                   headwall_candidates_out=hw_config["classification"]["headwall_candidates_out_centroid"],
                                   headwall_candidates_centroid_out=hw_config["classification"]["headwall_candidates_out"],
                                   rts_candidates_out=rts_config["classification"]["rts_candidates_out"],
                                   aoi_path=None,)
    else:
        logger.info('Using provided classified RTS objects'
                    '\n{}'.format(rts_classified))
        rts_objects = rts_classified

    #%%
    logger.info('Done')


if __name__ == '__main__':
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

    # Optional layers to provide, rather than computing from previous step
    alt_data = parser.add_argument_group('alt_data',
                                         'If any arguments in this group are '
                                         'provided, they will be used instead '
                                         'of the version created during the '
                                         'current run.')
    alt_data.add_argument('-hs', '--headwall_seg',
                        type=os.path.abspath)
    alt_data.add_argument('-hcln', '--headwall_cleaned',
                        type=os.path.abspath)
    alt_data.add_argument('-hz', '--headwall_zonal_stats',
                        type=os.path.abspath)
    # alt_data.add_argument('-h', '--headwall_classified',)
    
    alt_data.add_argument('-rs', '--rts_seg',
                        type=os.path.abspath)
    alt_data.add_argument('-rcln', '--rts_cleaned',
                        type=os.path.abspath)
    alt_data.add_argument('-rz', '--rts_zonal_stats',
                        type=os.path.abspath)
    alt_data.add_argument('-r', '--rts_classified',
                        type=os.path.abspath)

    os.chdir(r'E:\disbr007\umn\2020sep27_eureka')
    sys.argv = [r'C:\code\pgc-code-all\rts\rts.py',
                '-img', r'img\ortho_WV02_20140703\WV02_20140703013631_'
                        r'1030010032B54F00_14JUL03013631-M1BS-'
                        r'500287602150_01_P009_u16mr3413.tif',
                '-dem', r'dems\sel\WV02_20140703_1030010033A84300_'
                        r'1030010032B54F00\WV02_20140703_1030010033A84300_'
                        r'1030010032B54F00_2m_lsf_seg1_dem_masked.tif',
                '-prev_dem', r'dems\sel\WV02_20110811_103001000D198300_'
                             r'103001000C5D4600'
                             r'\WV02_20110811_103001000D198300_'
                             r'103001000C5D4600_2m_lsf_seg1_dem_masked.tif',
                '-pd', 'rts_test',
                '-aoi', r'aois\test_aoi.shp']

    args = parser.parse_args()

    image = args.image_input
    dem = args.dem_input
    dem_prev = args.previous_dem
    project_dir = args.project_dir
    aoi = args.aoi

    headwall_seg = args.headwall_seg
    headwall_cleaned = args.headwall_cleaned
    headwall_zonal_stats = args.headwall_zonal_stats
    # headwall_classified = args.headwall_classified

    rts_seg = args.rts_seg
    rts_cleaned = args.rts_cleaned
    rts_zonal_stats = args.rts_zonal_stats
    rts_classified = args.rts_classified

    main(image=image,
         dem=dem,
         dem_prev=dem_prev,
         project_dir=project_dir,
         aoi=aoi,
         headwall_seg=headwall_seg,
         headwall_cleaned=headwall_cleaned,
         headwall_zonal_stats=headwall_zonal_stats,
         rts_seg=rts_seg,
         rts_cleaned=rts_cleaned,
         rts_zonal_stats=rts_zonal_stats,
         rts_classified=rts_classified)
