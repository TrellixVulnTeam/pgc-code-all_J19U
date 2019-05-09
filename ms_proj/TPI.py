# -*- coding: utf-8 -*-
"""
Created on Sat Apr 27 22:00:43 2019

@author: disbr007

Calculates TPI at specified window size. Rather than moving a window across the
DEM, this method moves a copy of the entire DEM in the shape of the 'window', 
adding the value at each overlap. It counts the number of movements 

MODIFIED FROM:
Topographic position index for elevation models, 
a mock script to be tuned according to you needs.
Zoran Čučković
"""

import gdal
import numpy as np
from tqdm import tqdm

# -------------- INPUT -----------------
win_size = 121
elevation_model = r"E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\masked\2017_DEM_masked.utm.tif"
#elevation_model = r"E:/disbr007/umn/ms_proj/data/2019apr19_umiat_detach_zone/dems/2m/masked/WV02_2014_DEM_masked_trans.tif"
output_model = r"E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\masked\2017_TPIv2_{}.tif".format(win_size)
#output_model = r"E:/disbr007/umn/ms_proj/data/2019apr19_umiat_detach_zone/dems/2m/masked/2014_TPIv2_{}.tif".format(win_size)
count_model = r"E:\disbr007\umn\ms_proj\data\2019apr19_umiat_detach_zone\dems\2m\masked\count{}.tif".format(win_size)

# ----------  create the moving window  ------------
r= 5 #radius in pixels
#win = np.ones((2* r +1, 2* r +1))
# ----------   or, copy paste your window matrix -------------
#win_size = 100
win = np.ones((win_size, win_size), np.int32)

# window radius is needed for the function,
# deduce from window size (can be different for height and width…)
r_y, r_x  = win.shape[0]//2, win.shape[1]//2
win[r_y, r_x  ]=0  # let's remove the central cell 

def view (offset_y, offset_x, shape, step=1):
    """
    Function returning two matching numpy views for moving window routines.
    - 'offset_y' and 'offset_x' refer to the shift in relation to the analysed (central) cell 
    - 'shape' are 2 dimensions of the data matrix (not of the window!)
    - 'view_in' is the shifted view and 'view_out' is the position of central cells
    (see on LandscapeArchaeology.org/2018/numpy-loops/)
    """
    size_y, size_x = shape
    x, y = abs(offset_x), abs(offset_y)
    
    x_in = slice(x , size_x, step) 
    x_out = slice(0, size_x - x, step)

    y_in = slice(y, size_y, step)
    y_out = slice(0, size_y - y, step)
 
    # the swapping trick    
    if offset_x < 0: x_in, x_out = x_out, x_in                                 
    if offset_y < 0: y_in, y_out = y_out, y_in
 
    # return window view (in) and main view (out)
    return np.s_[y_in, x_in], np.s_[y_out, x_out]

# ----  main routine  -------

dem = gdal.Open(elevation_model)
dem_band = dem.GetRasterBand(1)
src_nodata = dem_band.GetNoDataValue()
mx_z = dem.ReadAsArray()
# Convert DEM NoData to 0.0
mx_z = np.where(mx_z == src_nodata, 0.0, mx_z)
nodata = 0.0 # CURRENTLY ONLY WORKS IF NO DATA == 0, add line to change array's NoData to 0...? Real 0's vs NoData zeros...

#matrices for temporary data
mx_temp = np.zeros(mx_z.shape)
mx_count = np.zeros(mx_z.shape)

# loop through window and accumulate values
for (y,x), weight in tqdm(np.ndenumerate(win)):
    
    if weight == 0 : continue  #skip zero values !
    # determine views to extract data 
    view_in, view_out = view(y - r_y, x - r_x, mx_z.shape)
    # using window weights (eg. for a Gaussian function)
    mx_temp[view_out] += mx_z[view_in] * weight
    ## ADD substract np.where(mx_z[view_in]==0, subtract -> mx_z[view_in] * weight, else do nothing)
   # track the number of neighbours 
   # (this is used for weighted mean : Σ weights*val / Σ weights)
    mx_count[view_out] += weight
    # Subtract number of times nodata value was included in the count
    # Where there is a zero in the moving window, substract 1 from the count, else do nothing (+0)
    mx_count[view_out] = np.where(mx_z[view_in]==0, mx_count[view_out] - 1, mx_count[view_out] + 0)
    

# Calculate TPI: (spot height – average neighbourhood height)
# Mask any NoData in the DEM from the 'temp' summed matrix
#mx_temp = np.where(mx_z == nodata, 0.0, mx_z)
#np.seterr(divide='ignore', invalid='ignore')
out = mx_z - mx_temp / mx_count
out = np.where(mx_z == 0.0, 0.0, out)

# Writing output TPI
driver = gdal.GetDriverByName('GTiff')
ds = driver.Create(output_model, mx_z.shape[1], mx_z.shape[0], 1, gdal.GDT_Float32)
ds.SetProjection(dem.GetProjection())
ds.SetGeoTransform(dem.GetGeoTransform())
ds.GetRasterBand(1).SetNoDataValue(0.0)
ds.GetRasterBand(1).WriteArray(out)
ds = None

# Write Count matrix for debugging
#driver = gdal.GetDriverByName('GTiff')
#ds = driver.Create(count_model, mx_count.shape[1], mx_count.shape[0], 1, gdal.GDT_Float32)
#ds.SetProjection(dem.GetProjection())
#ds.SetGeoTransform(dem.GetGeoTransform())
#ds.GetRasterBand(1).WriteArray(mx_count)
#ds.GetRasterBand(1).SetNoDataValue(src_nodata)
#ds = None