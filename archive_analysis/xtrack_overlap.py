import bisect
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, AutoLocator

from misc_utils.logging_utils import create_logger
from misc_utils.dataframe_plotting import y_fmt
from selection_utils.db import Postgres, generate_sql
#%%

logger = create_logger(__name__, 'sh', 'DEBUG')

db_name = 'danco.footprint'
xtrack_tbl = 'dg_imagery_index_xtrack_cc20'
geom = 'shape'
datediff = 'datediff'
mindd = 11
maxdd = 21
eap = "epsg:6933"
area_m = 'area_m'
area_interval = 'area_interval'
pairname = 'pairname'

# Plotting
area_bins = [0, 250, 500, 750, 1000, 1250, 5000]
area_intervals = ['[0, 250]', '[250, 500]',
                  '[500, 750]', '[750, 1000]',
                  '[1000, 1250]', '[1250, 5000]']

# SMALL_SIZE = 8
#
# MEDIUM_SIZE = 18
# BIGGER_SIZE = 24
#
# plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
# plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
# plt.rc('axes', labelsize=SMALL_SIZE)    # fontsize of the x and y labels
# plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
# plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
# plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
# plt.rc('figure', titlesize=SMALL_SIZE)  # fontsize of the figure title


def area_cat(area, cats):
    i = bisect.bisect_right(cats, area)
    return str(cats[i-1:i+1])

where = "{0} >= {1} AND {0} <= {2}".format(datediff,
                                           mindd,
                                           maxdd)
logger.info('Loading xtrack footprint...')
sql = generate_sql(xtrack_tbl, where=where, geom_col=geom, encode_geom_col='geom')
with Postgres('danco.footprint') as db_src:
    # ct = db_src.get_sql_count(sql)
    gdf = db_src.sql2gdf(sql=sql, geom_col='geom')

logger.info('Reprojecting...')
gdf_ea = gdf.to_crs(eap)

gdf_ea[area_m] = gdf_ea.area * 1e-6

# Add an area category
gdf_ea[area_interval] = gdf_ea[area_m].apply(lambda x: area_cat(x, area_bins))

# Get greater than 1000
gtr1000 = gdf_ea[gdf_ea[area_m] > 1000]
gtr1k_11_14 = gtr1000[gtr1000[datediff] <= 14]
gtr1k_11_14_ids = set(list(gtr1k_11_14['catalogid1']) + list(gtr1k_11_14['catalogid2']))

gtr1k_11_21 = gtr1000[gtr1000[datediff] <= 21]
gtr1k_11_21_ids = set(list(gtr1k_11_21['catalogid1']) + list(gtr1k_11_21['catalogid2']))

datediffs = [i for i in range(int(gdf_ea[datediff].min()),
                              int(gdf_ea[datediff].max())+1)]
gb = gdf_ea.groupby([datediff, area_interval]).agg({pairname: 'count'})
x = gb.unstack(datediff)
x.columns = x.columns.droplevel()
x = x.reindex(area_intervals)

#%%
plt.style.use('ggplot')
formatter = FuncFormatter(y_fmt)
mfig, maxes = plt.subplots(3, 4, figsize=(20,20))
maxes = maxes.flatten()
for i, dd in enumerate(datediffs):
    # Plot on a subplot
    x.loc[:, dd].plot(kind='bar', ax=maxes[i])
    maxes[i].yaxis.set_major_formatter(formatter)
    maxes[i].set_xlabel(dd)
    # Plot datediff on its own plot (and save)
    sfig, sax = plt.subplots(1, 1)
    x.loc[:, dd].plot(kind='bar', ax=sax)
    sax.yaxis.set_major_formatter(formatter)
    sax.set_title('Datediff: {}'.format(dd))
    sax.set_xlabel('Area Overlap')
    plt.title('Datediff: {}'.format(dd))
    plt.gcf().subplots_adjust(bottom=0.25)
    # sfig.savefig(r'C:\temp\xtrack_area_datediff{}.png'.format(dd))

#%% Plot area overlaps for datediff 11 thru 14
dd14 = x.loc[:, 11:14].sum(axis=1)
fig14, ax14 = plt.subplots(1, 1)
dd14.plot(kind='bar', ax=ax14, alpha=1, edgecolor='white', linewidth=1)
ax14.set_xlabel('Overlap Area (sqkm)')
ax14.yaxis.set_major_formatter(formatter)
ax14.set_title('Datediff: 11 - 14')
for i, v in enumerate(area_intervals):
    ax14.text(i-0.25, dd14[i]+(dd14.max()/60), '{:,}'.format(dd14[i]))
fig14.show()
fig14.savefig(r'C:\temp\xtrack_overlap11to14.png')

#%% Plot area overlaps for datediff 11 thru 21
dd21 = x.loc[:, 11:21].sum(axis=1)
fig21, ax21 = plt.subplots(1, 1)
dd21.plot(kind='bar', ax=ax21, alpha=1, edgecolor='white', linewidth=1)
ax21.set_xlabel('Overlap Area (sqkm)')
ax21.yaxis.set_major_formatter(formatter)
ax21.set_title('Datediff: 11 - 21')

for i, v in enumerate(area_intervals):
    ax21.text(i-0.25, dd21[i]+(dd21.max()/60), '{:,}'.format(dd21[i]))

fig21.show()
fig21.savefig(r'C:\temp\xtrack_overlap11to21.png')

