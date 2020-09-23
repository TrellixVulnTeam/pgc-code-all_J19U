try:
    from misc_utils.logging_utils import create_logger
except Exception as e:
    print('Error during import within {}'.format(__name__))
    raise e


logger = create_logger(__name__, 'sh', 'INFO')

# GDAL
logger.info('Testing GDAL import...')
try:
	from osgeo import gdal
except Exception as e:
	logger.info('Could not import gdal.')
	logger.info(e)
	raise(e)
logger.info('GDAL imported successfully...')

# OpenFileGDB
logger.info('Testing OpenFileGDB support...')



logger.info('Testing BigTIFF support...')
from bigtiff_support import test_bigtiff
test_bigtiff()


# Geopandas
try:
    import geopandas as gpd
except Exception as e:
    logger.error('Error during geopandas import')
    raise e

# Read Danco
try:
    import selection_utils.query_danco as query_danco
    logger.info('query_danco imported successfully.')
    x = query_danco.list_danco_db('footprint')
    x = query_danco.layer_fields('index_dg')
except Exception as e:
    logger.error('Error during query_danco test.')
    raise e
