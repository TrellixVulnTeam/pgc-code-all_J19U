import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
from subprocess import PIPE
import sys

from misc_utils.logging_utils import create_logger
from classify_rts import classify_rts

sys.path.append(Path(__file__).parent / "obia_utils")
from obia_utils.otb_lsms import otb_lsms
from obia_utils.otb_grm import otb_grm
from obia_utils.cleanup_objects import cleanup_objects
from obia_utils.calc_zonal_stats import calc_zonal_stats


#%%
logger = create_logger(__name__, 'sh', 'INFO')

CONFIG_FILE = Path(__file__).parent / 'config.json'
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


def main(headwall_seg=None,
         headwall_cleaned=None,
         headwall_zonal_stats=None,
         rts_seg=None,
         rts_cleaned=None,
         rts_zonal_stats=None,
         rts_classified=None):

    config = get_config()
    hw_config = config['headwall']
    rts_config = config['rts']

    #%% PREPROCESSING - Segment, calculate zonal statistics
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

    parser.add_argument('-hs', '--headwall_seg',
                        type=os.path.abspath)
    parser.add_argument('-hcln', '--headwall_cleaned',
                        type=os.path.abspath)
    parser.add_argument('-hz', '--headwall_zonal_stats',
                        type=os.path.abspath)
    # parser.add_argument('-h', '--headwall_classified',)
    
    parser.add_argument('-rs', '--rts_seg',
                        type=os.path.abspath)
    parser.add_argument('-rcln', '--rts_cleaned',
                        type=os.path.abspath)
    parser.add_argument('-rz', '--rts_zonal_stats',
                        type=os.path.abspath)
    parser.add_argument('-r', '--rts_classified',
                        type=os.path.abspath)

    args = parser.parse_args()

    headwall_seg = args.headwall_seg
    headwall_cleaned = args.headwall_cleaned
    headwall_zonal_stats = args.headwall_zonal_stats
    # headwall_classified = args.headwall_classified

    rts_seg = args.rts_seg
    rts_cleaned = args.rts_cleaned
    rts_zonal_stats = args.rts_zonal_stats
    rts_classified = args.rts_classified

    main(headwall_seg=headwall_seg,
         headwall_cleaned=headwall_cleaned,
         headwall_zonal_stats=headwall_zonal_stats,
         rts_seg=rts_seg,
         rts_cleaned=rts_cleaned,
         rts_zonal_stats=rts_zonal_stats,
         rts_classified=rts_classified)
