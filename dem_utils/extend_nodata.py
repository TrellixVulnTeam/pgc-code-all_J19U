from pathlib import Path

import rasterio
from shapely.geometry import Polygon
import geopandas as gpd

from misc_utils.logging_utils import create_logger
from misc_utils.raster_clip import clip_rasters


logger = create_logger(__name__, 'sh', 'INFO')

# Args
img = Path(r'E:\disbr007\umn\2020sep25_her\dems\WV02_20180621_1030010081ADA100_10300100800B1300_2m_lsf_v030400\WV02_20180621_1030010081ADA100_10300100800B1300_2m_lsf_seg5_dem_masked.tif')
distance = 2500

# Constants
ext_bb_mem = r'/vsimem/extended_bb.shp'

ds = rasterio.open(str(img))
left, bottom, right, top = ds.bounds
# bb = Polygon([(left, top), (right, top), (right, bottom), (left, bottom)])
# src_bb = gpd.GeoDataFrame(geometry=[bb], crs=ds.crs)

ext_left, ext_bottom, ext_right, ext_top = left-distance, bottom-distance, right+distance, top+distance
ext_bb = Polygon([(ext_left, ext_top), (ext_right, ext_top),
                  (ext_right, ext_bottom), (ext_left, ext_bottom)])
extended_bb = gpd.GeoDataFrame(geometry=[ext_bb], crs=ds.crs)
extended_bb.to_file(ext_bb_mem)

# import matplotlib.pylab as plt
#
# fig, ax = plt.subplots(1,1)
# src_bb.plot(color='none', edgecolor='blue', ax=ax)
# extended_bb.plot(color='none', edgecolor='red', ax=ax)
# fig.show()

clip_rasters(ext_bb_mem, str(img), out_dir=img.parent)