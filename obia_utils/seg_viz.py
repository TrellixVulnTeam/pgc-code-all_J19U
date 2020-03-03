# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:36:20 2020

@author: disbr007
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 14:07:13 2020

@author: Jeff Disbrow
"""

import tkinter

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib.widgets import Slider

import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd


root = tkinter.Tk()
root.wm_title("Embedding in Tk")

fig = Figure(figsize=(8, 8), dpi=100)
ax = fig.add_subplot(111)

## PLOT
gis_p = r'V:\pgc\data\scratch\jeff\ms\scratch\aoi6_good\seg\WV02_20150906_clip_ms_lsms_sr5rr200ss400_stats.shp'
gis = gpd.read_file(gis_p)
col = 'diff_mean'
gis.plot(ax=ax, color='none', edgecolor='black', linewidth=0.2, alpha=0.75)
cmin = gis[col].min()
cmax = gis[col].max()


## Add scale bar
#  TODO: Add checkboxes for fields to add new scalebars? or list fields to have scale bars    
w = tkinter.Scale(root, from_=cmin, to=cmax, digits=3, orient='horizontal',
                  sliderlength=15, length=300, width=30, resolution=0.01)
w.pack()

canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.draw()
canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

toolbar = NavigationToolbar2Tk(canvas, root)
toolbar.update()
canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)


def on_key_press(event):
    print("you pressed {}".format(event.key))
    key_press_handler(event, canvas, toolbar)


def update_plot():
    global gis
    ax.cla()
    val = w.get()
    new_gis = gis[gis[col] <= val]
    new_gis.plot(ax=ax, color='r', edgecolor='none')
    gis.plot(ax=ax, color='none', edgecolor='black', linewidth=0.2, alpha=0.75)
    print('Selected records: {}'.format(len(new_gis)))
    print('val = {}'.format(val))
    
    
tkinter.Button(root, text='Update Plot', command=update_plot).pack()

canvas.mpl_connect("key_press_event", on_key_press)


def _quit():
    root.quit()     # stops mainloop
    root.destroy()  # this is necessary on Windows to prevent
                    # Fatal Python Error: PyEval_RestoreThread: NULL tstate


button = tkinter.Button(master=root, text="Quit", command=_quit)
button.pack(side=tkinter.BOTTOM)

tkinter.mainloop()