from tqdm import tqdm
from shapely.geometry import Polygon, box
import geopandas as gpd

from archive_analysis.archive_analysis_utils import grid_aoi
from misc_utils.RasterWrapper import Raster


r_p = r'E:\disbr007\umn\2020sep27_eureka\img\ortho_WV02_20140703_test_aoi' \
      r'\WV02_20140703013631_1030010032B54F00_14JUL03013631-P1BS-' \
      r'500287602150_01_P009_u16mr3413_test_aoi.tif'

r = Raster(r_p)

bbox = r.bbox2gdf()

grid = grid_aoi(bbox, x_space=1, y_space=1)

x_pts = sorted(set(grid.geometry.values.x))
y_pts = sorted(set(grid.geometry.values.y))

all_cells = []
for i, x in tqdm(enumerate(x_pts)):
    if i == len(x_pts)-1:
        break
    next_x = x_pts[i+1]
    for j, y in enumerate(y_pts):
        if j == len(y_pts)-1:
            break
        next_y = y_pts[j+1]
        cell = box(x, y, next_x, next_y)
        all_cells.append(cell)


grid_poly = gpd.GeoDataFrame(geometry=all_cells, crs=grid.crs)
grid_poly.to_file(r'C:\temp\grid_poly.shp')