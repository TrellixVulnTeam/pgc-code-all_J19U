import rasterio as rio
from rasterio.features import shapes
from rasterio.fill import fillnodata
import rasterio.mask
# import fiona
import geopandas as gpd

from .gpd_utils import read_vec, write_gdf
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


def fill_internal_nodata(img:str , out: str, aoi: str) -> None:
    """
    Fills internal NoData gaps by interpolating across them.
    'Interal' gaps are definied as those within aoi polygon.
    TODO: Areas outside of AOI polygon are masked regardless of
     if they are NoData are not, so this effectively only works
     if the img is clipped to the AOI already. Workaround would
     be to create the aoi on the fly from the edges of the valid
     data in the img.
    """
    temp_filled = r'/vsimem/temp_filled.tif'
    with rio.open(img) as src:
        with rio.Env():
            profile = src.profile
            with rio.open(temp_filled, 'w', **profile) as dst:
                for i in range(src.count):
                    b = i + 1
                    arr = src.read(b)
                    mask = src.read_masks(b)
                    filled = fillnodata(arr, mask=mask)
                    dst.write(filled.astype(src.dtypes[i]), b)

    # with fiona.open(aoi) as shapefile:
    #     shapes = [feature['geometry'] for feature in shapefile]
    gdf = read_vec(aoi)
    shapes = gdf.geometry.values

    # Warn if not same CRS

    with rio.open(temp_filled) as src:
        if gdf.crs.to_wkt() != src.crs.to_wkt():
            logger.warning('AOI and raster to-be-filled do not have matching'
                           'CRS:\nAOI:{}\nRaster:{}'.format(gdf.crs, src.crs))
        out_img, out_trans = rasterio.mask.mask(src, shapes)
        with rio.open(out, 'w', **profile) as dst:
            dst.write(out_img)


def rio_polygonize(img: str, out_vec: str = None, band: int = 1, mask_value=None):
    logger.info('Polygonizing: {}'.format(img))
    with rio.Env():
        with rio.open(img) as src:
            arr = src.read(band)
            src_crs = src.crs
            if mask_value is not None:
                mask = arr == mask_value
            else:
                mask = None
            results = ({'properties': {'raster_val': v},
                        'geometry': s}
                       for i, (s, v) in
                       enumerate(shapes(arr,
                                        mask=mask,
                                        transform=src.transform)))
    geoms = list(results)
    gdf = gpd.GeoDataFrame.from_features(geoms, crs=src_crs)
    if out_vec:
        logger.info('Writing polygons to: {}'.format(out_vec))
        write_gdf(gdf, out_vec)

    return gdf
