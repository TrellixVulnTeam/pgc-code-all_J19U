# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 12:43:57 2020

@author: disbr007
"""
import logging
from misc_utils.logging_utils import create_logger, create_module_loggers

from obia_utils import test_logging


module_loggers = create_module_loggers('sh', 'INFO')

logger = create_logger(__name__, 'sh', handler_level='INFO')
logger.info('main message')
test_logging()
