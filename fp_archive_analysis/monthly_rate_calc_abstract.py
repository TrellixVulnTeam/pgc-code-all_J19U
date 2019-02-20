# -*- coding: utf-8 -*-
"""
Spyder Editor

Calculates number of unique ids and area for a given database by a given time period
"""

import geopandas as gpd
import pandas as pd
import os
import calendar
import datetime

### Function definitions
def choose_driver(in_db_path):
    '''Determines with Geopandas driver to use based on the path ending of the 
    input path'''
    file_extension = os.path.splitext(in_db_path)[-1]
    supported_extensions = {
            '.gdb': 'OpenFileGDB',
            '.shp': 'ESRI Shapefile',
            '.geojson': 'GeoJSON',
            '.json': 'JSON',
            '.sde': 'SDE',} # this won't work until a db connection is implemented
    if file_extension in supported_extensions:
        use_driver = supported_extensions[file_extension]
    else: 
        raise Exception('')
    return use_driver

def choose_aoi(user_input):
    '''Determines areas to group by'''
    # Area options to group imagery by
    area_dir = r'E:\disbr007\general'
    regions_path = os.path.join(area_dir, 'all_regions.shp')
    countries_path = os.path.join(area_dir, 'Countries_WGS84.shp')
    continents_path =  os.path.join(area_dir, 'continents.shp')
    supported_areas = {
            'regions': regions_path,
            'countries': countries_path,
            'continents': continents_path}
    areas = [key for key, value in supported_areas.items()]
    if user_input in supported_areas:
        use_aoi = supported_areas[user_input]
    else:
        use_aoi = None
        raise Exception('Area not supported. Choose from: {}'.format(areas))
    return use_aoi

# For naming outputs
now = datetime.datetime.now()
date = str(datetime.date.today())
year, month, day = date.split('-')
date_words = r'{}{}{}'.format(year, str.lower(calendar.month_abbr[int(month)]), day)

# Parent path
parent_path = r'C:\Users\disbr007\imagery'

# Database path to parse and layer name # change to user input
db_path = r'C:\Users\disbr007\imagery\imagery_index_stereo.gdb'
layer_name = None
layer_name = r'dg_imagery_index_stereo_cc20' # Default to None

# Read file to be worked on into geopandas
imagery_fp = gpd.read_file(db_path, driver=choose_driver(db_path), layer=layer_name) # may need to call function outside

# Read area option into geopandas
aoi_path = choose_aoi('regions') # change to user input

aoi = gpd.read_file(aoi_path, driver=choose_driver(db_path))

# Drop unnecessary fields
intrack_keep_fields = ['catalogid', 'acqdate',  'stereopair', 'cloudcover', 'platform', 'pairname', 'sqkm', 'sqkm_utm', 'geometry']
intrackDF = intrackDF[intrack_keep_fields]
xtrack_keep_fields = ['catalogid1', 'catalogid2', 'acqdate1', 'acqdate2', 'datediff', 'perc_ovlp', 'pairname', 'sqkm', 'geometry']
xtrackDF = xtrackDF[xtrack_keep_fields]

# Calculate yield of each pair
xtrackDF['yield_km'] = xtrackDF.perc_ovlp * xtrackDF.sqkm

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

# Change date field to be pandas datetime field for sorting by month
intrackDF['acqdate'] = pd.to_datetime(intrackDF['acqdate'])
xtrackDF['acqdate'] = pd.to_datetime(xtrackDF['acqdate1'])
xtrackDF = xtrackDF.drop('acqdate1', axis=1)

# Set datetime field to index for easier searching
intrackDF = intrackDF.set_index(['acqdate']) # and region?
xtrackDF = xtrackDF.set_index(['acqdate']) # and region?

intrackDF = intrackDF.resample('M').mean()
xtrackDF = xtrackDF.resample('M').mean()

#def df_date_range(df):
#    date_field = df.index
#    earliest = min(date_field)
#    latest = max(date_field)
#    return pd.date_range(earliest, latest)
#
#def fill_df_dates(df):
#    date_field = df.index
#    idx = df_date_range(df)
#    df.index = pd.DatetimeIndex(df.index)
#    df = df.reindex(idx, fill_value = 0)
#
#fill_df_dates(intrackDF)
#fill_df_dates(xtrackDF)

# Sort index - potentially unnecc.?
intrackDF.sort_index(inplace=True)
xtrackDF.sort_index(inplace=True)

# Create resampled dataframes by region, then year-month, counting unique catalog ids per year and month, suming area
monthlyIntrack = intrackDF.groupby([pd.Grouper(freq='M'), 'region']).agg({'catalogid': 'nunique', 'sqkm': 'sum'})
xtrack_aggregation = {
        'pairname': 'nunique', 
        'catalogid1': 'nunique', 
        'yield_km': 'sum', 
        'perc_ovlp': 'mean'
        }
monthlyXtrack = xtrackDF.groupby([pd.Grouper(freq='M'), 'region']).agg(xtrack_aggregation) # Count unique pairs of ids

# Unstack
monthlyIntrack = monthlyIntrack.unstack(level=1)
monthlyXtrack = monthlyXtrack.unstack(level=1)

# Add Totals columns
regions = ('antarctica', 'arctic', 'nonpolar')
perc_ovlpCols = [('perc_ovlp', x) for x in regions]
intrackAreaCols = [('sqkm', x) for x in regions]
intrackIDCols = [('catalogid', x) for x in regions]
xtrackYieldCols = [('yield_km', x) for x in regions]
xtrackPairCols = [('pairname', x) for x in regions]
xtrackIDCols = [('catalogid1', x) for x in regions]

monthlyIntrack['Total Area'] = monthlyIntrack[intrackAreaCols].sum(axis=1)
monthlyIntrack['Total Pairs'] = monthlyIntrack[intrackIDCols].sum(axis=1)

monthlyXtrack['Avg Overlap'] = monthlyXtrack[perc_ovlpCols].mean(axis=1)
monthlyXtrack['Total Area'] = monthlyXtrack[xtrackYieldCols].sum(axis=1)
monthlyXtrack['Total Pairs'] = monthlyXtrack[xtrackPairCols].sum(axis=1)
monthlyXtrack['Total Unique IDs'] = monthlyXtrack[xtrackIDCols].sum(axis=1)
monthlyXtrack['Avg Overlap'] = monthlyXtrack[perc_ovlpCols].mean(axis=1)

monthlyIntrack.reset_index(inplace=True)
monthlyXtrack.reset_index(inplace=True)

# Add month and year columns for excel chart formatting
monthlyIntrack['Month'] = monthlyIntrack['acqdate'].dt.month
monthlyIntrack['Year'] = monthlyIntrack['acqdate'].dt.year
monthlyIntrack['Month'] = monthlyIntrack['Month'].apply(lambda x: calendar.month_abbr[x])
# Reorder columns
cols = monthlyIntrack.columns.tolist()
colsOrder = [0, 10, 9, 8, 7, 1, 2, 3, 4, 5, 6]
cols = [cols[i] for i in colsOrder]
monthlyIntrack = monthlyIntrack[cols]

monthlyXtrack['Month'] = monthlyXtrack['acqdate'].dt.month
monthlyXtrack['Year'] = monthlyXtrack['acqdate'].dt.year
monthlyXtrack['Month'] = monthlyXtrack['Month'].apply(lambda x: calendar.month_abbr[x])
# Reorder columns
cols = monthlyXtrack.columns.tolist()
colsOrder = [0, 18, 17, 15, 14, 13, 16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
cols = [cols[i] for i in colsOrder]
monthlyXtrack = monthlyXtrack[cols]

monthlyIntrack.rename(index=str, columns={
        'acqdate': 'Date', 
        'catalogid': 'Pairs', 
        'sqkm': 'Area (sq. km)', 
        'arctic': 'Arctic', 
        'antarctica': 'Antarctica', 
        'nonpolar': 'Non-Polar'
        }, inplace=True)

monthlyXtrack.rename(index=str, columns={
        'acqdate': 'Date', 
        'pairname': 'Pairs', 
        'yield_km': 'Area (sq. km)', 
        'catalogid1': 'Unique Strips', 
        'arctic': 'Arctic', 
        'antarctica': 'Antarctica', 
        'nonpolar': 'Non-Polar'
        }, inplace=True)

# Combined monthly stereo
monthlyStereoDF = pd.concat([monthlyIntrack, monthlyXtrack]).groupby(['Date'], as_index=False).sum()
monthlyStereoDF = monthlyStereoDF.drop(['Unique Strips', 'perc_ovlp', 'Total Unique IDs', 'Avg Overlap'], axis=1)
monthlyStereoDF['month'] = monthlyStereoDF['Date'].dt.month
monthlyStereoDF['Year'] = monthlyStereoDF['Date'].dt.year
monthlyStereoDF['month'] = monthlyStereoDF['month'].apply(lambda x: calendar.month_abbr[x])
monthlyStereoDF.rename(columns={'month': 'Month'}, inplace=True) # Unable to create a column 'Month' directly for some reason...

# Node Hours Calc
monthlyStereoDF['Node Hours'] = monthlyStereoDF['Total Area'] / 16

# Only save overlapping date range
monthlyStereoDF = monthlyStereoDF.set_index(['Date'])

cols = monthlyStereoDF.columns.tolist()
colsOrder = [8, 9, 7, 6, 10, 0, 1, 2, 3, 4, 5]
cols = [cols[i] for i in colsOrder]
monthlyStereoDF = monthlyStereoDF[cols]

#monthlyStereoDF.reset_index(inplace=True)
#monthlyStereoDF = monthlyStereoDF.set_index(['Year', 'Month'])

earliestIn = min(monthlyIntrack['Date'])
earliestX = min(monthlyXtrack['Date'])
latestIn = max(monthlyIntrack['Date'])
latestX = max(monthlyXtrack['Date'])

begin = max(earliestIn, earliestX)
end = min(latestIn, latestX)

concur_monthlyStereoDF = monthlyStereoDF.loc[begin:end] # Overlapping dates for cross and in track stereo

# Write each dataframe to worksheet
excel_name = 'imagery_rates_{}.xlsx'.format(date_words)
excel_writer = pd.ExcelWriter(os.path.join(project_path, excel_name))
monthlyIntrack.to_excel(excel_writer, 'intrack', index=True)
monthlyXtrack.to_excel(excel_writer, 'xtrack', index=True)
monthlyStereoDF.to_excel(excel_writer, 'stereo', index=True)
concur_monthlyStereoDF.to_excel(excel_writer, 'concurrent_stereo', index=True)

excel_writer.save()



