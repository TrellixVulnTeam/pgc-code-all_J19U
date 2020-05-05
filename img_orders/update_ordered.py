from misc_utils.logging_utils import create_logger
from misc_utils.id_parse_utils import update_ordered


logger = create_logger(__name__, 'sh', 'INFO')
sublogger = create_logger('misc_utils.id_parse_utils', 'sh')

logger.info('Updating ordered IDs from sheets...')
update_ordered()
logger.info('Done.')
