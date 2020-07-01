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


plt.style.use('pycharm')

obj_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\seg\WV02_20140818_pca_MDFM_sr5_rr0x5_ms50_tx500_ty500.shp'
img_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\imagery\ps_clip\WV02_20140818201020_1030010035755C00_14AUG18201020-M1BS_R01C1-500106196120_03_P001_u16rf3413_clip.tif'

# Open data sources
logger.debug('Opening objects...')
obj = gpd.read_file(obj_p)
logger.debug('Opening imagery...')
img = rio.open(img_p)
logger.debug('Loading array')
img_arr = img.read()
logger.debug('Getting plotting extent..')
img_ext = plotting_extent(img)
logger.debug('Converting object crs to image crs..')
obj = obj.to_crs(img.crs)

img_kwargs={'stretch': True}

def plot_objects(obj=None, img=None, column=None, bounds_only=True,
                 cmap='viridis', linewidth=0.5, alpha=1,
                 edgecolor='white', rgb=[4, 2, 1], band=None,
                 ax=None, obj_kwargs={}, img_kwargs={}):
    """Plot vector objects on an image.
    Parameters:
        """
    # Create a figure and ax is not provided
    if not ax:
        fig, ax = plt.subplots(1,1, figsize=(15,15))
    # Plot the img if provided
    if img is not None:
        logger.debug('Plotting imagery...')
        if isinstance(img, rio.io.DatasetReader):
            img_arr = img.read()
            img_ext = plotting_extent(img)
        elif isinstance(img, os.path.abspath):
            i = rio.open(img)
            img_arr = i.read()
            img_ext = ep.plotting_ext(i)
        if band:
            ep.plot_bands(img_arr[band], extent=img_ext, ax=ax, **img_kwargs)
        else:
            ep.plot_rgb(img_arr, rgb=rgb, ax=ax, extent=img_ext, **img_kwargs)
    # Plot the objects if provided
    if obj is not None:
        logger.debug('Plotting objects...')
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
            obj.set_geometry(obj.geometry.boundary).plot(ax=ax, column=column, cmap=cmap, alpha=alpha,
                                                         linewidth=linewidth, **obj_kwargs)
        else:
            obj.plot(ax=ax, column=column, cmap=cmap, alpha=alpha,
                     linewidth=linewidth, edgecolor=edgecolor, **obj_kwargs)

    fig.show()

plot_objects(obj=obj, img=img, rgb=[5,3,2], bounds_only=True, img_kwargs=img_kwargs)