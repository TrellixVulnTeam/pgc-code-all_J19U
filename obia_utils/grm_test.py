import time
import os

from tqdm import tqdm
from pprint import pprint

from otb_grm import otb_grm, create_outname
from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')
create_logger('misc_utils.gdal_tools', 'sh', 'WARNING')
create_logger('otb_grm', 'sh', 'WARNING')

thesholds = [750]
iterations = [0]
specs = [0.5, 0.7]
spats = [100, 300]

od = r'E:\disbr007\umn\2020sep27_eureka\otb_grm_testing'
fmt = 'vector'
img = r'E:\disbr007\umn' \
      r'\2020sep27_eureka\img\ortho_WV02_20140703_test_aoi' \
      r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-' \
      r'M1BS-500287602150_01_P009_u16mr3413_pansh_test_aoi.tif'
criterion = 'bs'

logger.info('starting...')
for s in tqdm(specs, desc='spectral'):
    for t in tqdm(thesholds, desc='thresholds'):
        for i in tqdm(iterations, desc='iterations'):
            for p in tqdm(spats, desc='spatial'):
                print('\n\n')
                time.sleep(0.25)
                kwargs = {
                    'img': img,
                    'out_dir': od,
                    'out_format': fmt,
                    'threshold': t,
                    'criterion': criterion,
                    'niter': i,
                    'spectral': s,
                    'spatial': p,
                }
                for k, v in kwargs.items():
                    if k not in ['img', 'out_dir', 'out_format']:
                        logger.info('{}: {}'.format(k, v))
                outname = create_outname(**kwargs)
                if os.path.exists(outname):
                    logger.info('Out file exists, skipping: '
                                '{}'.format(os.path.basename(outname)))
                else:
                    otb_grm(**kwargs)
                logger.info('Run complete.\n\n\n')

logger.info('Done')
