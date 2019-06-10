# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 12:09:11 2018

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import os
import datetime
import sys
import argparse

sys.path.insert(0, r'C:\code\misc_utils')
from id_parse_utils import date_words

def type_parser(filepath):
    '''
    takes a file path (or dataframe) in and determines whether it is a dbf, 
    excel, txt, csv (or df), ADD SUPPORT FOR SHP****
    '''
    if type(filepath) == str:
        ext = os.path.splitext(filepath)[1]
        if ext == '.csv':
            with open(filepath, 'r') as f:
                content = f.readlines()
                for row in content[0]:
                    if len(row) == 1:
                        return 'id_only_txt' # txt or csv with just ids
                    elif len(row) > 1:
                        return 'csv' # csv with columns
                    else:
                        print('Error reading number of rows in csv.')
        elif ext == '.txt':
            return 'id_only_txt' 
        elif ext in ('.xls', '.xlsx'):
            return 'excel'
        elif ext == '.dbf':
            return 'dbf'
        elif ext == '.shp':
            return 'shp'
    elif isinstance(filepath, gpd.GeoDataFrame):
        
        return 'df'
    else:
        print('Unrecognized file type.')
    
    
def read_data(filepath):
    '''takes a file path in, determines type and reads data into dataframe accordingly'''
    file_type = type_parser(filepath)
    if file_type == 'csv':
        df = pd.read_csv(filepath)
    elif file_type == 'excel':
        df = pd.read_excel(filepath)
    elif file_type == 'id_only_txt':
        df = pd.read_csv(filepath, header=None, names=['catalogid'])
        platform_code = {
                '101': 'QB02',
                '102': 'WV01',
                '103': 'WV02',
                '104': 'WV03',
                '104A': 'WV03-SWIR',
                '105': 'GE01',
                '106': 'IK01'
                }
        
        df['platform'] = df['catalogid'].str.slice(0,3).map(platform_code).fillna('unk') # add platform columm to id only lists - TODO: does not account for SWIR..
    elif file_type == 'dbf':
        df = gpd.read_file(filepath)
    elif file_type == 'df':
        df = filepath
        # Rename 'catalogid1' column to 'catalogid' in the case of crosstrack database
        df.rename({'catalogid1': 'catalogid'})
    elif file_type == 'shp':
        print('Please use the .dbf file associated with the .shp.')
        sys.exit()
    else:
        df = None
        print('Error reading data into dataframe: {}'.format(filepath))
    print('IDs found: {}'.format(len(df.index)))
    return df


def clean_dataframe(dataframe):
    '''
    remove unnecessary columns, SWIR, duplicates. rename GE columns
    '''
    # Convert GE column names and values to DG style
    ge_cols_to_dg = {
            'image_id': 'catalogid',
            'source_abr': 'platform'
            }
    dataframe.rename(columns=ge_cols_to_dg, inplace=True)
    dataframe.platform.replace({'IK-2': 'IK01'}, inplace=True)
    
    # Remove unneccessary columns
    cols_of_int = ['catalogid','platform']
    print('Removing any duplicate ids...')
    dataframe = dataframe[cols_of_int].drop_duplicates(subset=cols_of_int) # Remove duplicate IDs
    dataframe = dataframe.drop_duplicates(subset=['catalogid', 'platform'], keep=False) # Can this line or the one above it be removed? Same thing right?
    print('Removing any SWIR ids...')
    dataframe = dataframe[~dataframe.catalogid.str.contains("104A")] # Drop SWIR - begins with 104A
#    dataframe.sort_values(by=['catalogid'], inplace=True)
    return dataframe


def list_chopper(platform_df, outpath, outnamebase, output_suffix, order_date):
    '''
    Takes a dataframe representing a platform and creates spreadsheets of 'n' ids where n is determined
    by the platform. The spreadsheets include only the catalog ids from that platform
    platform_df: dataframe of ids of one platform
    outpath: path to write sheets to
    outnamebase: base name to user for all orders
    output_suffix: order name
    '''
    platform = platform_df['platform'].iloc[0] # Determine platform of input dataframe
    
    # Look-up dictionary for number of rows per spreadsheet - TODO: make master dictionary with sheet size, name, catalog id prefix ('101', '102', etc.)
    platform_sheet_size = {
            'WV01': 1000,
            'WV02': 1000,
            'WV03': 1000, # change to 400 if Paul asks for smaller WV03 lists
            'GE01': 1000,
            'QB02': 1000,
            'IK01': 20000,
            'unk': 1000,
            }
    n = platform_sheet_size[platform] # Max length of each sheet 
    
    # Break this platform's dataframe into dfs of size det. above
    platform_list = [platform_df[i:i+n] for i in range(0, platform_df.shape[0], n)] 
    
    total_length = len(platform_list) # Total number of sheets for this platform
    
    platform_dict = {} # to store the dataframes for just this platform
    
    for i, df in enumerate(platform_list): # loop through this platforms dataframes (e.g. WV01 - 0:1000, WV01 - 1001:2000, WV01 - 2001:2200)
        # Add entry to dict - e.g. key = 'WV01_part1of2', val = 1000
        platform_dict[r'{}_part{}of{}'.format(platform, (int(i)+1), total_length)] = len(df)
        out_name = '{}{}_{}_{}_{}of{}.xlsx'.format(outnamebase, date_words(date=order_date), output_suffix, platform, (int(i)+1), total_length) # name of output sheet
        # Write sheet to excel file
        out_xl = os.path.join(outpath, out_name) # path of output sheet
        writer = pd.ExcelWriter(out_xl, engine='xlsxwriter')
        df.to_excel(writer, columns=['catalogid'], header=False, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format_txt = workbook.add_format({'num_format': '@'})
        worksheet.set_column(0,0,cell_format=format_txt)
        writer.save()
    return platform_dict


def write_master(dataframe, outpath, outnamebase, output_suffix, order_date):
    '''write all ids to master sheet for reference, to text file for entering into IMA'''
#    # Write master excel
#    master_name = os.path.join(outpath, '{}{}_{}_master.xlsx'.format(outnamebase, date_words(order_date), output_suffix))
#    master_writer = pd.ExcelWriter(master_name, engine='xlsxwriter')
#    dataframe.to_excel(master_writer, columns=['catalogid'], header=False, index=False, sheet_name='Sheet1')
#    master_writer.save()
    # Write text file
    txt_path = os.path.join(outpath, '{}{}_{}_master.txt'.format(outnamebase, date_words(order_date), output_suffix))
    dataframe.sort_index(inplace=True)
    dataframe.to_csv(txt_path, sep='\n', columns=['catalogid'], index=False, header=False)


def create_sheets(filepath, output_suffix, order_date, out_path=None):
    '''
    create sheets based on platforms present in list, including one formatted for entering into gsheets
    filepath: path to ids. can be txt, dbf, excel, csv, or dataframe
    output_suffix: order name to use in creation of sheets
    out_date: date to attach to order name and sheet names
    out_path: optional path to write sheets to, defaults to filepath parent directory
    '''
    # Determine type of filepath (str == file or dataframe)
    if type(filepath) == str: 
        # If an out path is provided use it, otherwise use the filepath directory
        if out_path:
            project_path = out_path
        else:
            project_path = os.path.dirname(filepath)
        # Read ids into dataframe
        dataframe = read_data(filepath)
    # If already a dataframe, an out_path must be provided to write sheets to
    elif isinstance(filepath, gpd.GeoDataFrame):
        dataframe = filepath
        project_path = out_path
    
    # Name to attached to all orders
    project_base = r'PGC_order_'
    # Remove unneccessary columns, rename others  
    dataframe = clean_dataframe(dataframe)
    
    # Create a nested dictionary for each platform
    all_platforms = dataframe.platform.unique().tolist() # list all platforms present in list
    print('{} platforms found: {}\n'.format(len(all_platforms), all_platforms))
    all_platforms_dict = {}
    for pf in all_platforms:
        all_platforms_dict[pf] = {} # create nested dict for each platform
        df = dataframe[dataframe['platform'] == pf] # create dataframe for each platform (select from master) 
        all_platforms_dict[pf]['df'] = df # store dataframe for each platform in its dict
        all_platforms_dict[pf]['g_sheet'] = list_chopper(df, project_path, project_base, output_suffix, order_date) # split dataframe into excel sheets
        print('{} IDs found: {}'.format(pf, len(df.index)))
    
    # Write sheet to copy to GSheet
    gsheet_path = os.path.join(project_path, '{}{}_{}_gsheet.xlsx'.format(project_base, date_words(order_date), output_suffix))
    gsheet_dict = {}
    for k in all_platforms_dict:
        gsheet_dict[k] = all_platforms_dict[k]['g_sheet']
    
    gsheet_df = pd.DataFrame.from_dict(gsheet_dict)
    gsheet_df['count'] = gsheet_df.sum(axis=1) 
    gsheet_df = gsheet_df['count']
    gsheet_writer = pd.ExcelWriter(gsheet_path, engine='xlsxwriter')
    gsheet_df.to_excel(gsheet_writer, index=True, sheet_name='Sheet1')
    gsheet_writer.save()
    write_master(dataframe, project_path, project_base, output_suffix, order_date)
    return all_platforms_dict

#input_file = r"E:\disbr007\imagery_orders\test\catalogs_to_reorder.txt" # for debugging
#out_suffix = 'test_order_chop'
#create_sheets(input_file, out_suffix)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str, help="File containing ids. Supported types: csv, dbf, xls, xlsx, txt")
    parser.add_argument("out_name", type=str, help="Output sheets suffix. E.g. 'PGC_order_2019_[out_name]_WV01_1of2'")
    parser.add_argument("--order_date", type=str, help="Date to attach to order. E.g. '2019-02-21'")
    parser.add_argument("--out_path", type=str, help="Directory to write sheets to.")
    
    args = parser.parse_args()
    
    input_file = args.input_file
    out_suffix = args.out_name
    order_date = args.order_date 
    out_path = args.out_path
    
        
    print("Creating sheets...\n")
    create_sheets(filepath=input_file, output_suffix=out_suffix, order_date=order_date, out_path=out_path)
    print('\nComplete.')
