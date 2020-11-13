from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mc
import numpy as np

import rasterio as rio
from rasterio.plot import show
from sklearn import cluster
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

from misc_utils.RasterWrapper import Raster

plt.style.use('ggplot')
figsize = (10, 10)
#%%
def compute_bic(kmeans, X):
    """
    Computes the BIC metric for a given clusters

    Parameters:
    -----------------------------------------
    kmeans:  List of clustering object from scikit learn

    X     :  multidimension np array of data points

    Returns:
    -----------------------------------------
    BIC value
    """
    # assign centers and labels
    centers = [kmeans.cluster_centers_]
    labels  = kmeans.labels_
    #number of clusters
    m = kmeans.n_clusters
    # size of the clusters
    n = np.bincount(labels)
    #size of data set
    N, d = X.shape

    #compute variance for all clusters beforehand
    cl_var = (1.0 / (N - m) / d) * sum([sum(distance.cdist(X[np.where(labels == i)], [centers[0][i]],
             'euclidean')**2) for i in range(m)])

    const_term = 0.5 * m * np.log(N) * (d+1)

    BIC = np.sum([n[i] * np.log(n[i]) -
               n[i] * np.log(N) -
             ((n[i] * d) / 2) * np.log(2*np.pi*cl_var) -
             ((n[i] - 1) * d/ 2) for i in range(m)]) - const_term

    return(BIC)

#%%
prj_dir = Path(r'E:\disbr007\umn\2020sep27_eureka')

# img_path = prj_dir / Path(r'img\ndvi_WV02_20140703_test_aoi'
#                            r'\WV02_20140703013631_1030010032B54F00_'
#                            r'14JUL03013631-M1BS-500287602150_01_P009_u16mr3413_'
#                            r'pansh_test_aoi_ndvi_test_aoi.tif')
img_path = prj_dir / Path(r"img\ortho_WV02_20140703_test_aoi"
                          r"\WV02_20140703013631_1030010032B54F00_14JUL03013631"
                          r"-P1BS-500287602150_01_P009_u16mr3413_test_aoi.tif")

img_raster = rio.open(img_path)

# print(img_raster.meta)
# img_arr = img_raster.read(1, masked=True)

#%% Plot image
# vmin, vmax = np.nanpercentile(img_arr.compressed(), (5,95))
# fig, ax = plt.subplots(1, 1, figsize=figsize)
# show(img_raster, cmap='Greys', vmin=vmin, vmax=vmax, ax=ax)
# plt.tight_layout()
# fig.show()

#%%
imgxyb = np.empty((img_raster.height, img_raster.width, img_raster.count),
                  img_raster.meta['dtype'])
for band in range(imgxyb.shape[2]):
    imgxyb[:, :, band] = img_raster.read(band+1)

img1d = imgxyb[:, :, :3].reshape((imgxyb.shape[0]*imgxyb.shape[1],
                                  imgxyb.shape[2]))
img1d_ma = np.ma.masked_where(img1d == -9999, img1d)

#%% BIC
ks = range(1, 10)
kclusters = []
for i in ks:
    print('N Clusters: {}'.format(i))
    kclusters.append(cluster.KMeans(n_clusters=i).fit(img1d_ma))

print('Computing BIC...')
bics = [compute_bic(kc, img1d_ma) for kc in kclusters]

#%% Plot BICs
fig, ax = plt.subplots(1, 1, figsize=figsize)
ax.plot(ks[:], bics[:])
fig.show()
#%% Get N for minimum
n_min_BIC = bics[1:].index(min(bics[1:])) - 1
n_min_BIC = 5

#%% KMeans with one n
cl = cluster.KMeans(n_clusters=n_min_BIC)
param = cl.fit(img1d_ma)

img_cl = cl.labels_
img_cl = img_cl.reshape(imgxyb[:, :, 0].shape)

#%% Plot K-Means clustered image
cmap = mc.LinearSegmentedColormap.from_list("", ["black", "red", "green",
                                                 "yellow"])

fig, ax = plt.subplots(1, 1, figsize=figsize)
ax.imshow(img_cl, cmap=cmap)
plt.axis('off')
fig.show()

#%% Write K-Means clustered image
src_raster = Raster(str(img_path))
src_raster.WriteArray(img_cl, str(prj_dir / 'k_means{}.tif'.format(n_min_BIC)))

