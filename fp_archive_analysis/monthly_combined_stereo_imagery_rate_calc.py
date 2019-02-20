# -*- coding: utf-8 -*-
"""
Spyder Editor

Calculates number of unique ids for xtrack and intrack imagery by month. Also calcs area and yield (xtrack only)
"""

import geopandas as gpd
import pandas as pd
import os
import calendar
import datetime

def df_limit_date_range(df, start, stop):
    '''limits a df to date range'''
    df = df.loc[start:stop]
    return df

def add_totals(df, cols_list):
    '''Adds a column to a dataframe summing based on regions'''
    regions = ('Antarctica', 'Arctic', 'Non-Polar') # change to be input list of multi-index col name parts
    df_cols = df.columns.tolist()
    for col in cols_list:
        totals_col = 'Total ' + col 
        regional_cols = [(col, x) for x in regions]
        if set(regional_cols).issubset(df_cols):
            df[totals_col] = df[regional_cols].sum(axis=1)
    return df

# For naming outputs
now = datetime.datetime.now()
date = str(datetime.date.today())
year, month, day = date.split('-')
date_words = r'{}{}{}'.format(year, str.lower(calendar.month_abbr[int(month)]), day)

# Project path
project_path = r'C:\Users\disbr007\imagery'

# Data paths
intrack_gdb_path = r'C:\Users\disbr007\imagery\imagery_index_stereo.gdb'
xtrack_gdb_path = r'C:\Users\disbr007\imagery\dg_cross_track_2019jan09_deliv.gdb'
regions_path = r'E:\disbr007\imagery_rates\data\all_regions.shp'

# Read feature classes into geopandas
intrackDF = gpd.read_file(intrack_gdb_path, driver='OpenFileGDB', layer='dg_imagery_index_stereo_cc20')
xtrackDF = gpd.read_file(xtrack_gdb_path, crs = {'init': 'espg:4326'}, driver='OpenFileGDB', layer='dg_imagery_index_all_cc20_xtrack_pairs_jan09_prj_WGS')
regionsDF = gpd.read_file(regions_path, driver='ESRI Shapefile')

print('Data loaded into geopandas...')

# Drop unnecessary fields
intrack_keep_fields = ['catalogid', 'acqdate',  'stereopair', 'cloudcover', 'platform', 'pairname', 'sqkm', 'sqkm_utm', 'geometry']
intrackDF = intrackDF[intrack_keep_fields]
xtrack_keep_fields = ['catalogid1', 'catalogid2', 'acqdate1', 'acqdate2', 'datediff', 'perc_ovlp', 'pairname', 'sqkm', 'geometry']
xtrackDF = xtrackDF[xtrack_keep_fields]

# Join to regions to identify region of each id, by identifying centroid location
intrackDF['centroid'] = intrackDF.centroid
intrackDF = intrackDF.set_geometry('centroid')
intrackDF = gpd.sjoin(intrackDF, regionsDF, how='left', op='within')
intrackDF = intrackDF.set_geometry('geometry')
intrackDF = intrackDF.drop('centroid', axis=1)

xtrackDF['centroid'] = xtrackDF.centroid
xtrackDF = xtrackDF.set_geometry('centroid')
xtrackDF = gpd.sjoin(xtrackDF, regionsDF, how='left', op='within')
xtrackDF = xtrackDF.set_geometry('geometry')
xtrackDF = xtrackDF.drop('centroid', axis=1)

print('Spatial joins complete')

# Change date field to be pandas datetime field for sorting by month
intrackDF['acqdate'] = pd.to_datetime(intrackDF['acqdate'])
xtrackDF['acqdate'] = pd.to_datetime(xtrackDF['acqdate1'])
xtrackDF = xtrackDF.drop('acqdate1', axis=1)

# Set datetime field to index for easier searching
intrackDF = intrackDF.set_index(['acqdate']) # and region?
xtrackDF = xtrackDF.set_index(['acqdate']) # and region?

# Fill in missing dates - may not be working?
#intrackDF = intrackDF.resample('M').mean()
#xtrackDF = xtrackDF.resample('M').mean()

# Sort index - potentially unnecc.?
intrackDF.sort_index(inplace=True)
xtrackDF.sort_index(inplace=True)

# Create resampled dataframes by region, then year-month, counting unique catalog ids per year and month, suming area
monthlyIntrack = intrackDF.groupby([pd.Grouper(freq='M'), 'region']).agg({'catalogid': 'nunique', 'sqkm': 'sum'})
monthlyIntrack['Unique Strips'] = monthlyIntrack['catalogid'] * 2
xtrack_aggregation = {
        'pairname': 'nunique', 
        'catalogid1': 'nunique', 
        'sqkm': 'sum', 
#        'perc_ovlp': 'mean'
        }

monthlyXtrack = xtrackDF.groupby([pd.Grouper(freq='M'), 'region']).agg(xtrack_aggregation) # Count unique pairs of ids
monthlyXtrack_1k = xtrackDF[xtrackDF['sqkm'] > 999].groupby([pd.Grouper(freq='M'), 'region']).agg(xtrack_aggregation)
monthlyXtrack_500 = xtrackDF[(xtrackDF['sqkm'] > 499) & (xtrackDF['sqkm'] < 1000)].groupby([pd.Grouper(freq='M'), 'region']).agg(xtrack_aggregation)
monthlyXtrack_250 = xtrackDF[(xtrackDF['sqkm'] > 249) & (xtrackDF['sqkm'] < 500)].groupby([pd.Grouper(freq='M'), 'region']).agg(xtrack_aggregation)

final_dfs = {
        'intrack': monthlyIntrack,
        'xtrack': monthlyXtrack,
        'xtrack_1k': monthlyXtrack_1k,
        'xtrack_500': monthlyXtrack_500,
        'xtrack_250': monthlyXtrack_250,
        }


cols_to_total = ['Area (sq. km)', 'Pairs', 'Unique Strips']

col_rename = { 
        'acqdate': 'Date', 
        'catalogid': 'Pairs', # intrack pairs column
        'sqkm': 'Area (sq. km)',  # intrack area col
        'pairname': 'Pairs',  # xtrack pairs column
        'sqkm': 'Area (sq. km)', # xtrack area column
        'catalogid1': 'Unique Strips', # xtrack unique ids column
        'arctic': 'Arctic', 
        'antarctica': 'Antarctica', 
        'nonpolar': 'Non-Polar'
        }

for k, v in final_dfs.items():
    final_dfs[k] = final_dfs[k].unstack(level=1)
    final_dfs[k] = final_dfs[k].reset_index()
    final_dfs[k].rename(index=str, columns=col_rename, inplace=True) # Rename columns
    
# Combined monthly stereo
monthly_combined_stereo = pd.concat([final_dfs['intrack'], final_dfs['xtrack_1k']]).groupby(['Date'], as_index=False).sum()
final_dfs['combined_stereo'] = monthly_combined_stereo # Add combined to dataframe dictionary

for k, v in final_dfs.items():
#    final_dfs[k].unstack(level=1) # Unstack
    final_dfs[k] = add_totals(final_dfs[k], cols_to_total) # Add totals columns
    # Add Month and Year columns for charting
    final_dfs[k]['Month'] = final_dfs[k]['Date'].dt.month
    final_dfs[k]['Month'] = final_dfs[k]['Month'].apply(lambda x: calendar.month_abbr[x])
    final_dfs[k]['Year'] = final_dfs[k]['Date'].dt.year
    final_dfs[k]['Node Hours'] = final_dfs[k]['Total Area (sq. km)'].div(16.) # Node Hours Calc
    final_dfs[k] = final_dfs[k].round(0)
    final_dfs[k] = final_dfs[k][[
            ('Date', ''),('Month', ''),('Year', ''),
            ('Total Area (sq. km)', ''),('Total Pairs', ''),('Total Unique Strips', ''),('Node Hours', ''),
            ('Area (sq. km)', 'Antarctica'),('Area (sq. km)', 'Arctic'),('Area (sq. km)', 'Non-Polar'),
            ('Pairs', 'Antarctica'),('Pairs', 'Arctic'),('Pairs', 'Non-Polar'),
            ('Unique Strips', 'Antarctica'),('Unique Strips', 'Arctic'),('Unique Strips', 'Non-Polar')
            ]]
#    final_dfs[k] = final_dfs[k][columns_order]

#del monthlyIntrack, monthlyXtrack, monthly_combined_stereo

# Only save overlapping date range
date_format = "%d/%m/%Y %H:%M:%S"
early_str = '01/01/1900 00:00:00'
early_date = datetime.datetime.strptime(early_str, date_format)
late_str = '01/01/9999 00:00:00'
late_date = datetime.datetime.strptime(late_str, date_format)
begin = early_date
end = late_date
for k, v in final_dfs.items():
#    final_dfs[k].reset_index(inplace=True, drop=False)
    if min(final_dfs[k]['Date']) > begin:
        begin = min(final_dfs[k]['Date'])
    else:
        begin = begin
    if max(final_dfs[k]['Date']) < end:
        end = max(final_dfs[k]['Date'])
    else:
        end = end
    final_dfs[k] = final_dfs[k][final_dfs[k]['Date'].between(begin,end)]
    final_dfs[k] = final_dfs[k].loc[final_dfs[k]['Date'] < '2019-01-01'] # Drop data newer than end of 2018 

# Write each dataframe to worksheet and pickle
excel_name = 'imagery_rates_{}.xlsx'.format(date_words)
excel_writer = pd.ExcelWriter(os.path.join(project_path, excel_name))
for name, df in final_dfs.items():
    df.to_excel(excel_writer, name, index=True)
    df.to_pickle(os.path.join(project_path, '{}.pkl'.format(name)))
excel_writer.save()