# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 20:14:51 2019

@author: disbr007
"""
import pandas as pd
import matplotlib.pyplot as plt

table_path = r"C:\Users\disbr007\imagery\imagery_rates_2019feb13.xlsx"

df = pd.read_excel(table_path, sheet_name='xtrack')

pd.to_datetime(df['Date'])

df.set_index(['Date'], inplace=True)

fig, ax = plt.subplots()
ax.atackplot(df.index, df['])