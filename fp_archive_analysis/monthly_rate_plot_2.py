# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 16:35:49 2019

@author: disbr007
attempt to use matplotlib to plot monthly archive
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

pickle_path = r'C:\Users\disbr007\imagery\not_onhand\xtrack.pkl'
df = pd.read_pickle(pickle_path)

#fig, ax = plt.subplots()
#
##df.plot(ax=axes, subplots=True)
#df.plot(y=('Unique_Strips', False, 'WV01'), ax=ax)

sns.set()
sns.pairplot(df, hue='day')