#%% Load written candidates with 'truth'
# hwc_shp = gpd.read_file(r'E:\disbr007\umn\2020sep27_eureka\scratch\hwc_truth.shp')
# # Drop everything but truth and index
# hwc_shp = hwc_shp[['index', 'truth']]
# hwc_shp.set_index('index', inplace=True)
#
# hwc = hwc.objects[hwc.objects[hw_candidate]==True]
# hwc = hwc.join(hwc_shp)

# %% Plot headwall candidate characteristics
# alpha = 0.5
# linewidth = 2
# vline_color = 'red'
# atts = {rug_mean: high_rugged,
#         sa_rat_mean: high_sa_rat,
#         slope_mean: high_slope,
#         ndvi_mean: low_ndvi,
#         med_mean: low_med,
#         }
# adj_atts = {best_low_curv: low_curv,
#             best_high_curv: high_curv,
#             best_low_med: low_med}
#
# fig, axes = plt.subplots(3, 3, figsize=(15, 10))
# axes = axes.flatten()
#
# truth_filter = hwc[truth] == 'true_yes'
# for i, (k, v) in enumerate(atts.items()):
#     axes[i].set_title(k)
#     # hwc[[k]].hist(k, alpha=alpha, label='F', ax=axes[i])
#     axes[i].hist([hwc[k][truth_filter], hwc[k][~truth_filter]],
#                  stacked=True,
#                  label=['true_yes', 'true_no'] if i == 0 else "",
#                  alpha=alpha)
#     axes[i].axvline(v, linewidth=linewidth, color=vline_color)
#
# for j, (k, v) in enumerate(adj_atts.items()):
#     axes[i+j+1].hist([hwc[~hwc[k].isnull()][best_low_curv].apply(lambda x: x[1])[truth_filter],
#                       hwc[~hwc[k].isnull()][best_low_curv].apply(lambda x: x[1])[~truth_filter]],
#                      alpha=alpha,
#                      stacked=True),
#     axes[i+j+1].set_title(k)
#     axes[i+j+1].axvline(v, linewidth=linewidth, color=vline_color)
#
# l = fig.legend(loc="upper left")
# plt.tight_layout()
# fig.show()

