import numpy as np
from numpy.lib import stride_tricks
import matplotlib.pyplot as plt
from skimage import io
from sklearn.feature_extraction import image
import scipy
import cv2


dem_p = r'V:\pgc\data\scratch\jeff\ms_proj_2019jul05\dems\raw\raw\SETSM_WV01_20160413_102001004EA97100_102001004C845700_seg1_2m_v3.0_dem.tif'

#dem_p = r'C:\temp\SETSM_WV01_20160413_102001004EA97100_102001004C845700_seg1_2m_v3_trans.tif'
dem = cv2.imread(dem_p)

#dem = np.ones((50, 50))
#dem[2:6, 2:6] = 5
#dem[0, 1] = 2
#dem[1, 0] = 2


def calc_tpi(dem, size):
    '''
    OpenCV implementation of TPI
    dem: array
    size: int, kernel size in x and y directions (square kernel)
    '''
    kernel = np.ones((size,size),np.float32)/(size*size)
    dem_conv = cv2.filter2D(dem, -1, kernel, borderType=2)
    tpi = dem - dem_conv
    
    return tpi


#def calc_tpi(dem, size):
#    '''
#    Scipy implementation of TPI. Need to account for edge cases.
#    '''
#    dem_conv = scipy.ndimage.uniform_filter(dem, output=np.float32, size=size)
#    tpi = dem - dem_conv
#    return tpi



## PLOTTING
sizes = [3]
cols = len(sizes) // 2
rows = int(len(sizes) / cols)
index = 1
col_i = 0
row_i = 0

fig, axes = plt.subplots(nrows=rows, ncols=cols)

for sz in sizes:
    tpi = calc_tpi(dem, sz)
    ax = axes[row_i, col_i]
    ax.imshow(tpi, cmap='RdBu')
    ax.set_title(sz)


    col_i += 1
    
    
    if col_i >= cols:
        col_i = 0
        row_i += 1
    
    ax.set_yticklabels([])
    ax.set_xticklabels([])
plt.tight_layout()
