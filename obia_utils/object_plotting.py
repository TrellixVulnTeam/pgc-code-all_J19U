import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import numpy as np

from osgeo import gdal
from rasterio.plot import show, plotting_extent
import rasterio as rio
import geopandas as gpd
import earthpy.plot as ep
from misc_utils.RasterWrapper import Raster

# plt.style.use('pycharm')
#
# obj_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\seg\WV02_20140818_sr5_rr1x0_ms400_tx500_ty500.shp'
# img_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\imagery\ps_clip\WV02_20140818201020_1030010035755C00_14AUG18201020-M1BS_R01C1-500106196120_03_P001_u16rf3413_clip.tif'
#
# # Open data sources
# obj = gpd.read_file(obj_p)
# img = rio.open(img_p)
# img_arr = img.read()
# img_ext = plotting_extent(img)
# obj = obj.to_crs(img.crs)


def plot_objects(column, obj=None, img=None, bounds_only=True,
                 cmap='viridis', linewidth=0.5, alpha=1,
                 edgecolor='white', rgb=[4, 2, 1], band=None,
                 ax=None, obj_kwargs={}, img_kwargs={}):

    if not ax:
        fig, ax = plt.subplots(1,1, figsize=(15,15))
    if img:
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

    if obj:
        obj = obj.to_crs(img.crs)
        if bounds_only:
            obj[obj[column] >= 0].set_geometry(obj.geometry.boundary).plot(ax=ax,
                                                                           column=column,
                                                                           cmap=cmap,
                                                                           linewidth=linewidth,
                                                                           **obj_kwargs)
        else:
            obj[obj[column] >= 0].plot(ax=ax,
                                       column=column,
                                       cmap=cmap,
                                       linewidth=linewidth,
                                       edgecolor=edgecolor,
                                       **obj_kwargs)

    fig.show()
