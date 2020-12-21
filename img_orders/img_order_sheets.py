# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 12:09:11 2018

@author: disbr007
"""

import pandas as pd
import geopandas as gpd
import os, datetime, sys, argparse, re
import pprint

from misc_utils.id_parse_utils import date_words, mfp_ids
from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

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
                        logger.info('Error reading number of rows in csv.')
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
        logger.info('Unrecognized file type.')
    
    
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
        df = gpd.read_file(filepath)
        # logger.info('Please use the .dbf file associated with the .shp.')
        # sys.exit()
    else:
        df = None
        logger.info('Error reading data into dataframe: {}'.format(filepath))

    # Reduce to just catalogid and platform columns
    df = df[['catalogid', 'platform']]

    logger.info('Source IDs found: {:,}'.format(len(df.index)))
    
    return df


def clean_dataframe(dataframe, keep_swir, out_path=None, drop_mfp=False,
                    drop_online_only=False):
    '''
    remove unnecessary columns, SWIR, duplicates. rename GE columns
    '''
    # Function to clean the names 
    def locate_swir(row): 
        # Search for opening bracket in the name followed by 
        # any characters repeated any number of times 
        if re.search('^104A[a-zA-Z0-9_.-]*', row['catalogid']): 
            return 'WV03-SWIR' 
        else:
            return row['platform']
    
    # Convert GE column names and values to DG style
    ge_cols_to_dg = {
            'image_id': 'catalogid',
            'source_abr': 'platform',
            'vehicle': 'platform'
            }
    dataframe.rename(columns=ge_cols_to_dg, inplace=True)
    dataframe.platform.replace({'IK-2': 'IK01'}, inplace=True)

    # Remove unneccessary columns
    cols_of_int = ['catalogid','platform']
    logger.info('Removing any duplicate ids...')
    len_b4 = len(dataframe)
    dataframe = dataframe[cols_of_int].drop_duplicates(subset=cols_of_int) # Remove duplicate IDs
    dataframe = dataframe.drop_duplicates(subset=['catalogid', 'platform'], keep=False) # Can this line or the one above it be removed? Same thing right?
    len_after = len(dataframe)
    if len_b4 != len_after:
        logger.info('Duplicates removed: {:,}'.format(len_b4 - len_after))
        logger.info('Remaining IDs: {:,}'.format(len_after))
    dataframe['platform'] = dataframe.apply(locate_swir, axis=1)

    # Remove onhand
    if drop_mfp:
        logger.info('Dropping IDs in MFP...')
        if drop_online_only:
            logger.info('(Online only)')
        len_b4 = len(dataframe)
        dataframe = dataframe[~dataframe['catalogid'].isin(mfp_ids(online=drop_online_only))]
        len_after = len(dataframe)
        if len_b4 != len_after:
            logger.info('IDs found in MFP and removed: {}'.format(len_b4-len_after))
        else:
            logger.info('No IDs found in MFP.')

    if len(dataframe) == 0:
        logger.warning('No remaining IDs in source. Exiting.')
        sys.exit()

    return dataframe


def list_chopper(platform_df, outpath, outnamebase, output_suffix, order_date, fullname):
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
            'WV03-SWIR': 1000,
            }
    n = platform_sheet_size[platform] # Max length of each sheet 
    
    # Break this platform's dataframe into dfs of size det. above
    platform_list = [platform_df[i:i+n] for i in range(0, platform_df.shape[0], n)] 
    
    # Find lists smaller than 100 and add them back to the last df
    if len(platform_list) > 1:
        for i, each_df in enumerate(platform_list):
            if len(each_df) < 100:
                try:
                    new_df = pd.concat([platform_list[i], platform_list[i-1]])
                    del platform_list[i], platform_list[i-1]
                    platform_list.append(new_df)
                except IndexError:
                    new_df = pd.concat([platform_list[i], platform_list[i+1]])
                    del platform_list[i], platform_list[i-1]
                    platform_list.append(new_df)
    
    total_length = len(platform_list) # Total number of sheets for this platform
    
    platform_dict = {} # to store the dataframes for just this platform
    
    for i, df in enumerate(platform_list): # loop through this platforms dataframes (e.g. WV01 - 0:1000, WV01 - 1001:2000, WV01 - 2001:2200)
        # Add entry to dict - e.g. key = 'WV01_part1of2', val = 1000
        platform_dict[r'{}_part{}of{}'.format(platform, (int(i)+1), total_length)] = len(df)
        if fullname:
            out_name = '{}_{}_{}of{}.xlsx'.format(fullname, platform, (int(i)+1), total_length)
        else:
            out_name = '{}{}_{}_{}_{}of{}.xlsx'.format(outnamebase, date_words(date=order_date), 
                                                       output_suffix, platform, (int(i)+1), total_length) # name of output sheet
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


def write_master(dataframe, outpath, outnamebase, output_suffix, order_date, keep_swir, fullname):
    '''write all ids to master sheet for reference, to text file for entering into IMA'''
#    # Write master excel
#    master_name = os.path.join(outpath, '{}{}_{}_master.xlsx'.format(outnamebase, date_words(order_date), output_suffix))
#    master_writer = pd.ExcelWriter(master_name, engine='xlsxwriter')
#    dataframe.to_excel(master_writer, columns=['catalogid'], header=False, index=False, sheet_name='Sheet1')
#    master_writer.save()
    # Write text file
    if fullname:
        txt_path = os.path.join(outpath, '{}_master.txt'.format(fullname))
    else:
        txt_path = os.path.join(outpath, '{}{}_{}_master.txt'.format(outnamebase, date_words(order_date), output_suffix))
    
    if keep_swir == True:
        # Keep SWIR
        pass
    else:
        # Default - Drop SWIR from master text
        len_b4 = len(dataframe)
        dataframe = dataframe[dataframe['platform'] != 'WV03-SWIR']
        len_after = len(dataframe)
        if len_b4 != len_after:
            logger.info('Removed SWIR: {:,}'.format(len_b4-len_after))
    dataframe = dataframe.sort_index()
    dataframe = dataframe.sort_values(by='catalogid')
    dataframe.to_csv(txt_path, sep='\n', columns=['catalogid'], index=False, header=False)


def create_sheets(filepaths, output_suffix, order_date, keep_swir, fullname, out_path=None,
                  drop_mfp=False, drop_online_only=False):
    '''
    create sheets based on platforms present in list, including one formatted for entering into gsheets
    filepath: path to ids. can be txt, dbf, excel, csv, or dataframe
    output_suffix: order name to use in creation of sheets
    out_date: date to attach to order name and sheet names
    out_path: optional path to write sheets to, defaults to filepath parent directory
    '''
    dataframe = pd.DataFrame()
    for filepath in filepaths:
        # Determine type of filepath (str == file or dataframe)
        if type(filepath) == str:
            logger.info('Reading IDs from: {}'.format(filepath))
            # If an out path is provided use it, otherwise use the filepath directory
            if out_path:
                project_path = out_path
            else:
                project_path = os.path.dirname(filepath)
            # Read ids into dataframe
            df = read_data(filepath)
        # If already a dataframe, an out_path must be provided to write sheets to
        elif isinstance(filepath, (pd.DataFrame, gpd.GeoDataFrame)):
            logger.info('Reading preloaded dataframe of IDs...')
            df = filepath
            project_path = out_path
        # logger.info('IDs found: {}'.format(len(df)))
        dataframe = pd.concat([dataframe, df])

    logger.info('Total IDs found: {:,}'.format(len(dataframe)))

    # Remove unneccessary columns, rename others
    dataframe = clean_dataframe(dataframe, keep_swir, project_path,
                                drop_mfp=drop_mfp, drop_online_only=drop_online_only)

    # Drop any duplicates
    dataframe = dataframe.drop_duplicates(subset='catalogid')

    
    # Create a nested dictionary for each platform
    ids_written = 0
    all_platforms = dataframe.platform.unique().tolist() # list all platforms present in list
    logger.info('{} platforms found: {}\n'.format(len(all_platforms), all_platforms))
    if keep_swir:
        pass
    else:
        if 'WV03-SWIR' in all_platforms:
            logger.info('Removing SWIR...\n')
            all_platforms.remove('WV03-SWIR')
            # Name to attached to all orders
    project_base = r'PGC_order_'
    all_platforms_dict = {}
    for pf in all_platforms:
        all_platforms_dict[pf] = {} # create nested dict for each platform
        df = dataframe[dataframe['platform'] == pf] # create dataframe for each platform (select from master) 
        all_platforms_dict[pf]['df'] = df # store dataframe for each platform in its dict
        all_platforms_dict[pf]['g_sheet'] = list_chopper(df, project_path, project_base, output_suffix, order_date,
                                                         fullname=fullname) # split dataframe into excel sheets
        logger.info('{} IDs found: {:,}'.format(pf, len(df.index)))
        ids_written += len(df.index)
        
    # Write sheet to copy to GSheet
    if fullname:
        gsheet_path = os.path.join(project_path, '{}_gsheet.xlsx'.format(fullname))
    else:
        gsheet_path = os.path.join(project_path, '{}{}_{}_gsheet.xlsx'.format(project_base, date_words(order_date), output_suffix))
    gsheet_dict = {}
    
    for k in all_platforms_dict:
#        gsheet_dict[k] = all_platforms_dict[k]['g_sheet']
        gsheet_dict.update(all_platforms_dict[k]['g_sheet'])
    
    gsheet_df = pd.Series(gsheet_dict, name='count')
    gsheet_df = pd.DataFrame(gsheet_df)

    # Sort by platform, then sheet number
    gsheet_df.index.name = 'sheet_name'
    gsheet_df['plat'] = list(gsheet_df.reset_index(level=0)['sheet_name'].apply(lambda x: x.split('_part')[0]))
    gsheet_df['sort'] = list(gsheet_df.reset_index(level=0)['sheet_name'].apply(lambda x: x.split('_part')[1].split('of')[0]))

    logger.info(gsheet_df)
    gsheet_df['sort'] = gsheet_df['sort'].astype(int)
    gsheet_df.sort_values(['plat','sort'], inplace=True)
    gsheet_df.drop('sort', axis=1)
    
    gsheet_writer = pd.ExcelWriter(gsheet_path, engine='xlsxwriter')
    gsheet_df.to_excel(gsheet_writer, index=True, sheet_name='Sheet1')
    gsheet_writer.save()
    write_master(dataframe, project_path, project_base, output_suffix, order_date, keep_swir, 
                 fullname=fullname)
    logger.info('IDs written to sheets: {:,}'.format(ids_written))

    return all_platforms_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_files", type=str, nargs='+',
                        help="File containing ids. Supported types: csv, dbf, xls, xlsx, txt")
    parser.add_argument("-o", "--out_name", type=str,
                        help="Output sheets suffix. E.g. 'PGC_order_2019_[out_name]_WV01_1of2'")
    parser.add_argument('--drop_mfp', action='store_true',
                        help='Removing any IDs found in the master footprint before creating sheets.')
    parser.add_argument('--drop_online_only', action='store_true',
                        help='When used with --drop_mfp, drop only online or '
                             'tape records, keep offline in sheets.')
    parser.add_argument("-fn", "--fullname", type=str,
                        help="""Overwrite default naming schema and use what is provided here plus sensor
                                and sheet numbers.""")
    parser.add_argument("--order_date", type=str, default=datetime.datetime.now().strftime('%Y-%m-%d'), 
                        help="Date to attach to order. E.g. '2019-02-21'")
    parser.add_argument("--out_path", type=str, help="Directory to write sheets to.")
    parser.add_argument("--keep_swir", action='store_true', 
                        help="Use flag to write a list of SWIR IDs")

    # sys.argv = [r'C:\code\pgc-code-all\img_orders\img_order_sheets.py',
    #             '-i',
    #             r'E:\disbr007\imagery_orders\NASA_order_2020dec17_adapt_replenish'
    #             '\SSAr2.2_all_zones_missing_ntflist_ids.txt',
    #             '-fn',
    #             'NASA_order_2020dec17_adapt_replenish',
    #             '--drop_mfp',
    #             '--drop_online_only',
    # ]

    args = parser.parse_args()
    
    input_files = args.input_files
    out_suffix = args.out_name
    fullname = args.fullname
    order_date = args.order_date 
    out_path = args.out_path
    keep_swir = args.keep_swir # True/False
    drop_mfp = args.drop_mfp
    drop_online_only = args.drop_online_only
        
    logger.info("Creating sheets...\n")
    create_sheets(filepaths=input_files, output_suffix=out_suffix,
                  fullname=fullname, order_date=order_date, 
                  keep_swir=keep_swir, out_path=out_path,
                  drop_mfp=drop_mfp, drop_online_only=drop_online_only)

    logger.info('Complete.')
