import matplotlib.pyplot as plt
import numpy as np

from osgeo import gdal
from rasterio.plot import show, plotting_extent
import rasterio as rio
import geopandas as gpd
import earthpy.plot as ep
from misc_utils.RasterWrapper import Raster

plt.style.use('pycharm_blank')

def normalize(array):
    array_min, array_max = array.min(), array.max()

    return (array - array_min) / (array_max - array_min)


obj_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\seg\WV02_20140818_sr5_rr1x0_ms400_tx500_ty500.shp'
img_p = r'V:\pgc\data\scratch\jeff\ms\2020may12\imagery\ps_clip\WV02_20140818201020_1030010035755C00_14AUG18201020-M1BS_R01C1-500106196120_03_P001_u16rf3413_clip.tif'

# Open data sources
obj = gpd.read_file(obj_p)
img = rio.open(img_p)
img_arr = img.read()
img_ext = plotting_extent(img)
obj = obj.to_crs(img.crs)



# img = Raster(img_p)
# blue = img.GetBandAsArray(2)
# green = img.GetBandAsArray(3)
# red = img.GetBandAsArray(5)
# nir = img.GetBandAsArray(7)
# nblue = normalize(blue)
# ngreen = normalize(green)
# nred = normalize(red)
# nnir = normalize(nir)

# fcc = np.dstack([nnir, nred, ngreen])
fig, ax = plt.subplots(1,1, figsize=(15,15))

ep.plot_rgb(img_arr, rgb=[5,3,2], ax=ax, extent=img_ext)
# obj.plot(ax=ax, color='none', edgecolor='white', linewidth=0.1)
fig.show()

# TODO: plot multispectral (convert arrays to geo coordinates or objects to pixel coords...)
