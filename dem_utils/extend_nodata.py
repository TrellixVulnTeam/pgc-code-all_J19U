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


def extend_no_data(img, distance, out_path=None, out_dir=None, out_suffix=None):
    """Extend the no-border boundary of the passed img raster by
    distance in units of img CRS
    Useful for extending DEM boundaries to ensure entire image is
    covered when ortho-ing.
    Parameters
    ---------
    img : str
        Raster file path to be extended.
    distance : float
        Distance to extend raster in units of raster CRS
    out_path : str
        Full path to write extended raster to.
    out_dir : str
        Directory to write extended raster to, with
        specified out_suffix.
    out_suffix : str
        Suffix to append to img file name when providing
        out_dir only.

    Returns
    -------
    out_path : str
        Full path that extended raster is ultimately written to.
    """
    # Create out_path if not provided
    if not out_path:
        img_p = Path(img)
        if not out_dir:
            out_dir = img_p.parent
        if not out_suffix:
            out_suffix = 'ext{}'.format(round(distance))
        out_path = out_dir / '{}_{}{}'.format(img_p.stem, out_suffix, img_p.suffix)

    # Get current bounds
    logger.info('Reading bounds of input: {}'.format(img))
    ds = rasterio.open(str(img))
    left, bottom, right, top = ds.bounds
    logger.info('Current bounds\n'
                'Left:   {}\nBottom: {}\nRight:  {}\nTop:    {}'.format(left, bottom, right, top))

    ext_left, ext_bottom, ext_right, ext_top = left-distance, bottom-distance, right+distance, top+distance
    logger.info('Extended bounds\n'
                'Left:   {}\nBottom: {}\nRight:  {}\nTop:    {}'.format(ext_left, ext_bottom, ext_right, ext_top))
    ext_bb = Polygon([(ext_left, ext_top), (ext_right, ext_top),
                      (ext_right, ext_bottom), (ext_left, ext_bottom)])
    extended_bb = gpd.GeoDataFrame(geometry=[ext_bb], crs=ds.crs)
    ext_bb_mem = r'/vsimem/extended_bb.shp'
    logger.debug('Writing extended bounding box to in-memory dataset: {}'.format(ext_bb_mem))
    extended_bb.to_file(ext_bb_mem)

    clip_rasters(ext_bb_mem, str(img), out_path=out_path)
