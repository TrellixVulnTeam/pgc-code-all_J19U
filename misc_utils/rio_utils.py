import rasterio as rio
from rasterio.fill import fillnodata
import rasterio.mask
import fiona


def fill_internal_nodata(img, out, aoi):
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

    with fiona.open(aoi) as shapefile:
        shapes = [feature['geometry'] for feature in shapefile]

    with rio.open(temp_filled) as src:
        out_img, out_trans = rasterio.mask.mask(src, shapes)
        with rio.open(out, 'w', **profile) as dst:
            dst.write(out_img)
