# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 22:43:20 2018

@author: disbr007
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter 
import matplotlib.dates as mdates

pickle_path = r'E:\disbr007\imagery_rates\scripts\pickles'

monthlyStereo = pd.read_pickle(os.path.join(pickle_path, 'monthly_stereo.pkl'))
monthlyXtrack = pd.read_pickle(os.path.join(pickle_path, 'monthly_xtrack.pkl'))
monthlyXtrack_single = pd.read_pickle(os.path.join(pickle_path, 'monthly_xtrack_single.pkl'))
stereoDF = pd.read_pickle(os.path.join(pickle_path, 'stereoDF.pkl'))
xtrackDF = pd.read_pickle(os.path.join(pickle_path, 'xtrackDF.pkl'))

monthlyStereo = monthlyStereo.unstack(level=1)

# Replace NAN with 0
dfs = [monthlyStereo, monthlyXtrack, monthlyXtrack_single]
for df in dfs:
    df.fillna(0, inplace=True)
    df.index = df.index.to_pydatetime()

def millions(x, pos):
    'The two args are the value and tick position'
    return '%1.1fM' % (x*1e-6)

formatter = FuncFormatter(millions)

date_s, date_e = '2015-01-01', '2018'
figsize = (18, 6)
date_fmt = mdates.DateFormatter('%Y-%b')

fig2 = plt.figure()
fig2.suptitle('Digital Globe Stereo Archive', fontsize=14)
fig2.set_tight_layout(True)

# Intrack Stereo 
# ID count lines
ax1 = fig2.add_subplot(121)
ax1.set_title('Intrack')
ln3 = monthlyStereo[date_s : date_e].plot(y=[('catalogid','nonpolar')], figsize=figsize, grid=False, ax=ax1, legend=None, label=['Nonpolar ID\'s'], color='#800000')
ln5 = monthlyStereo[date_s : date_e].plot(y=[('catalogid', 'antarctica')], figsize=figsize, grid=False, ax=ax1, legend=None, label=['Antarctica ID\'s'], color='#000080')
ln7 = monthlyStereo[date_s : date_e].plot(y=[('catalogid', 'arctic')], figsize=figsize, grid=False, ax=ax1, legend=None, label=['Arctic ID\'s'], color='#206020')

# Area lines
linestyle = '--'
ax2 = ax1.twinx()
ax2.yaxis.set_major_formatter(formatter)
ln4 = monthlyStereo[date_s : date_e].plot(y=[('sqkm','nonpolar')], figsize=figsize, grid=False, ax=ax2, legend=None, label=['Nonpolar Area'], color='#ff6666', linestyle=linestyle)
ln6 = monthlyStereo[date_s : date_e].plot(y=[('sqkm', 'antarctica')], figsize=figsize, grid=False, ax=ax2, legend=None, label=['Antarctica Area'], color='#9999ff',  linestyle=linestyle)
ln8 = monthlyStereo[date_s : date_e].plot(y=[('sqkm', 'arctic')], figsize=figsize, grid=False, ax=ax2, legend=None, label=['Arctic Area'], color='#79d279',  linestyle=linestyle)

# Legend Creation
ax1lines, ax1labels = ax1.get_legend_handles_labels()
ax2lines, ax2labels = ax2.get_legend_handles_labels()
ax1.legend([ax1lines[0], ax2lines[0], ax1lines[1], ax2lines[1], ax1lines[2], ax2lines[2]], [ax1labels[0], ax2labels[0], ax1labels[1], ax2labels[1], ax1labels[2], ax2labels[2]], frameon=False, loc='best')

# Label axis
ax1.set_xlabel('Date')
ax1.set_ylabel('Count')
ax1.set_ylim(bottom=0)
ax1.set_ylim(top=12000)
ax2.set_ylabel('Area (sq. km)')
ax2.set_ylim(bottom=0)
ax2.set_ylim(top=65e6)


# Xtrack Stereo
# ID count lines
ax3 = fig2.add_subplot(122)
ax3.set_title('Cross Track')
ln13 = monthlyXtrack_single[date_s : date_e].plot(y=[('catalogid1','nonpolar')], figsize=figsize, grid=False, ax=ax3, legend=None, label=['Nonpolar ID\'s'], color='#800000')
ln15 = monthlyXtrack_single[date_s : date_e].plot(y=[('catalogid1', 'antarctica')], figsize=figsize, grid=False, ax=ax3, legend=None, label=['Antarctica ID\'s'], color='#000080')
ln17 = monthlyXtrack_single[date_s : date_e].plot(y=[('catalogid1', 'arctic')], figsize=figsize, grid=False, ax=ax3, legend=None, label=['Arctic ID\'s'], color='#206020')

        
# Area lines
linestyle = '--'
ax4 = ax3.twinx()
ax4.yaxis.set_major_formatter(formatter)
ln14 = monthlyXtrack_single[date_s : date_e].plot(y=[('yield_sqkm','nonpolar')], figsize=figsize, grid=False, ax=ax4, legend=None, label=['Nonpolar Area'], color='#ff6666', linestyle=linestyle)
ln16 = monthlyXtrack_single[date_s : date_e].plot(y=[('yield_sqkm', 'antarctica')], figsize=figsize, grid=False, ax=ax4, legend=None, label=['Antarctica Area'], color='#9999ff',  linestyle=linestyle)
ln18 = monthlyXtrack_single[date_s : date_e].plot(y=[('yield_sqkm', 'arctic')], figsize=figsize, grid=False, ax=ax4, legend=None, label=['Arctic Area'], color='#79d279',  linestyle=linestyle)

ax3.set_xlabel('Date')
ax3.set_ylabel('Count')
#ax3.set_ylim(bottom=0)
ax4.set_ylabel('Area (sq. km)')
ax3.set_ylim(bottom=0)
ax4.set_ylim(bottom=0)
ax4.set_ylim(top=65e6)
ax3.xaxis.set_major_formatter(date_fmt)
ax4.xaxis.set_major_formatter(date_fmt)
ax2.xaxis.set_major_formatter(date_fmt)
ax1.xaxis.set_major_formatter(date_fmt)

#axes = [ax1, ax2, ax3, ax4]
#for ax in axes:
#    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%M'))
#    
#    months = mdates.YearLocator(1, month=6)
#    years = mdates.MonthLocator((1,5,10))
#    monthsFmt = mdates.DateFormatter('%b')
#    yearsFmt = mdates.DateFormatter('%Y')
#    # Minor labels
#    ax.xaxis.set_minor_locator(months)
#    ax.xaxis.set_minor_formatter(monthsFmt)
#    # Major Labels
#    ax.xaxis.set_major_locator(years)
#    ax.xaxis.set_major_formatter(yearsFmt)
#    ax.grid(which='both', axis='x')
#    for tick in ax.get_xaxis().get_major_ticks():
#        tick.set_pad(15)



