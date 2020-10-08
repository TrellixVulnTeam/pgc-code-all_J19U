import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import numpy as np

from osgeo import gdal
from rasterio.plot import show, plotting_extent
import rasterio as rio
import geopandas as gpd
import earthpy.plot as ep

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'DEBUG')

def geo2pixel(y, x, img):
    """
    Convert geographic coordinates to pixel coordinates
    """
    xres, xrot, ulx, yrot, yres, uly, *_rest = img.transform
    geotransform = [ulx, xres, xrot, uly, yrot, yres]
    row = int(np.around((y - geotransform[3]) / geotransform[5]))
    col = int(np.around((x - geotransform[0]) / geotransform[1]))

    return row, col


def plot_objects(obj=None, img=None, column=None, bounds_only=True, obj_extent=True,
                 obj_cmap=None, linewidth=0.5, alpha=1,
                 edgecolor='white', rgb=[4, 2, 1], band=None,
                 ax=None, obj_kwargs={}, img_kwargs={}):
    """Plot vector objects on an image
    Parameters:
        """
    # Create a figure and ax is not provided
    if not ax:
        fig, ax = plt.subplots(1,1, figsize=(15,15))
    # Plot the img if provided
    if img is not None:
        logger.debug('Plotting imagery...')
        # If path to image provided, open it, otherwise assumed open rasterio DatasetReader
        if isinstance(img, str):
            img = rio.open(img)
        img_arr = img.read(masked=True)
        if obj is not None and obj_extent:
            minx, miny, maxx, maxy = obj.total_bounds
            minrow, mincol = geo2pixel(y=maxy, x=minx, img=img)
            maxrow, maxcol = geo2pixel(y=miny, x=maxx, img=img)
            img_arr = img_arr[:, mincol:maxcol, minrow:maxrow]
            logger.debug(img_arr.min(), img_arr.max())
            img_ext = (minx, maxx, miny, maxy)
        else:
            img_ext = plotting_extent(img)
        logger.debug('Img ext: {}'.format(img_ext))
        if band is not None:
            ep.plot_bands(img_arr[band-1], extent=img_ext, ax=ax, **img_kwargs)
        else:
            ep.plot_rgb(img_arr, rgb=rgb, ax=ax, extent=img_ext, **img_kwargs)

    # Plot the objects if provided
    if obj is not None:
        logger.debug('Plotting objects...')
        if img is not None:
            obj = obj.to_crs(img.crs)
        # If a column is not provided, plot all as the same color
        if column is None:
            # Create temporary column, ensuring it doesn't exist
            logger.debug('Creating a temporary column for plotting')
            column = np.random.randint(10000)
            while column in list(obj):
                column = 'temp_{}'.format(np.random.randint(10000))

            obj[column] = 1
        if bounds_only:
            obj.set_geometry(obj.geometry.boundary).plot(ax=ax, column=column, cmap=obj_cmap, alpha=alpha,
                                                         linewidth=linewidth, **obj_kwargs)
        else:
            obj.plot(ax=ax, column=column, cmap=obj_cmap, alpha=alpha,
                     linewidth=linewidth, edgecolor=edgecolor, **obj_kwargs)


    fig.show()


#%%
# plt.style.use('ggplot')
#
# obj_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\seg\grm\WV02_20140818_pca_MDFM_bst10x0ni30s0spec1x0spat0x5.shp'
# img_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\dems\pca\max_diff_from_mean\WV02_20140818_pca_MDFM.tif'
# # %%
# # Open data sources
# logger.debug('Opening objects...')
# seg = gpd.read_file(obj_p)
# logger.debug('Opening imagery...')
# img = rio.open(img_p)
#
# img_kwargs = {}
# plot_objects(obj=seg, img=img, band=0, bounds_only=True, obj_extent=True, obj_cmap=None,
#              img_kwargs=img_kwargs, obj_kwargs={'color': 'white'})
