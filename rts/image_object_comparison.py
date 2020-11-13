import matplotlib.pyplot as plt
from pathlib import Path

from shapely.geometry import Polygon, box
import geopandas as gpd

plt.style.use('pycharm')
#%% Paths
project_path = Path(r'E:\disbr007\umn\2020sep27_eureka')
objects_path = project_path / (r'seg\zs\WV02_20140703013631_1030010032B54F00_'
                               r'14JUL03013631-M1BS-500287602150_01_P009_'
                               r'u16mr3413_pansh_test_aoi_'
                               r'bst175x0ni0s0spec0x3spat25x0_zs.shp')
rts_digit_path = project_path / (r'tks_loc\disbrow_digitized.shp')

#%% Load
objects = gpd.read_file(objects_path)
rts_all = gpd.read_file(rts_digit_path)

#%% Get only RTS within objects
# [box(ulx, lry, lrx, uly) for ulx, lry, lrx, uly in bbs]
lx, ly, rx, uy = objects.total_bounds
bbox = gpd.GeoDataFrame(geometry=[box(lx, ly, rx, uy)], crs=objects.crs)

rts_all['centroid'] = rts_all.geometry.centroid
rts_all = rts_all.set_geometry('centroid')
rts = gpd.sjoin(rts_all, bbox)
rts = rts.set_geometry('geometry')

#%% Identify objects within RTS
# objects['centroid'] = objects.geometry.centroid
# objects = objects.set_geometry('centroid')
objects['rts'] = objects.geometry.centroid.apply(
    lambda x: any([x.within(r) for r in rts.geometry]))

#%% Plot
fig, ax = plt.subplots(1, 1, figsize=(20,20))
objects.plot(ax=ax, column='MED_mean', edgecolor='grey', linewidth=0.2,
             vmin=-0.5, vmax=0.5)
# rts.plot(ax=ax, color='none', edgecolor='red', linewidth=1)
(objects[objects['rts']==True].dissolve(by='rts')
 .plot(ax=ax, color='none',edgecolor='red', linewidth=1.25))
fig.show()

