# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 13:49:34 2019

@author: disbr007
Copies aerial imagery from offline drives or server to specified destination.
"""

import argparse
import copy
import os
import logging
import shutil
import sys

import geopandas as gpd
from tqdm import tqdm
import enlighten

from query_danco import query_footprint


### Inputs
#selection_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\3948\ahap\selected_ahap_photo_extents.shp'
#dst_dir = r'C:\temp\ahap'
#src_loc = 'drives'
#SERIES = 'both' #'both' # 'high_res', 'medium_res'


def main(selection, destination, source_loc, high_res, med_res,
         list_drives, list_missing_paths, write_copied, 
         exclude_list, dryrun, verbose):
    #### Logging setup
    log = 'ahap_copier.log'
    logging.basicConfig(level=logging.DEBUG,
                        filemode='w', 
                        filename=log,)
    # create logger
    logger = logging.getLogger('ahap_copier')
#    logger.setLevel(logging.DEBUG)
    # create file handler
    fh = logging.FileHandler(log)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    if verbose is True:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.debug('Log file created at: {}'.format(log))
    
    
    ## Params
    SERVER_LOC = os.path.normpath(r'V:\pgc\data\aerial\usgs\ahap\photos')
    PHOTO_EXTENTS = 'Photo_Extents'
    FLIGHTLINES = 'Flightlines'
    CAMPAIGN = 'AHAP'
    JOIN_SEL = 'PHOTO_ID'
    JOIN_FP = 'UNIQUE_ID'
    FP = 'usgs_index_aerial_image_archive'
    DB = 'imagery'
    FILEPATH = 'filepath'
    FILENAME = 'filename'
    SRC_DRIVE = 'src_drive'
    SERIES_FIELD = 'SERIES'
    SERIES_BOTH = 'both'
    SERIES_HIGH = 'high_res'
    SERIES_MED = 'medium_res'
    
    
    DRIVE_PATH = 'drive_path'
    MNT_PATH = 'mounted_path'
    NOT_MOUNTED = 'NOT_MOUNTED'
    RELATIVE_PATH = 'relative_path'
    SERVER_PATH = 'server_path'
    FROM_DRIVE = 'drives'
    FROM_SERVER = 'server'
    DST_PATH = 'dst'
    DST_EXISTS = 'dst_exists'
    SRC_PATH = 'src'
    
        
    def get_active_drives():
        """
        List all active drives.
        """
        drive_list = []
        for drive in range(ord('A'), ord('Z')):
            if os.path.exists(chr(drive) + ':'):
                drive_list.append(chr(drive) + ':')
        return drive_list
    
    
    ## Build server paths
    def create_relative_paths(row, FILENAME):
        """
        Create relative path for each row
        """
        # Determine series subdir (high or low)
        if row['series'] == 'high_res':
            resolution = 'high'
        elif row['series'] == 'medium_res':
            resolution = 'med'
        
        roll_dir = 'AB{}ROLL'.format(row[FILENAME][:-8])
        
        relative_path = os.path.join(resolution, roll_dir, row[FILENAME])
        
        return relative_path
    
    
    def find_drive_location(row, active_drives, DRIVE_PATH):
        """
        Check if each row (file) is on any of the active drives.
        If so return that drive letter.
        """
        # TODO: Figure out how to handle missing files -> subset aia before copying
        possible_filepaths = [os.path.join(letter, row[DRIVE_PATH]) for letter in active_drives]
        actual_filepath = [fp for fp in possible_filepaths if os.path.exists(fp)]
        if len(actual_filepath) == 0:
            filepath = NOT_MOUNTED
        elif len(actual_filepath) == 1:
            filepath = actual_filepath[0]
        else:
            filepath = 'TWO LOCATIONS?'
        
        
    
        return filepath            
                
    
    def find_server_location(row):
        if os.path.exists(row[SERVER_PATH]):
            filepath = row[SERVER_PATH]
        else:
            filepath = 'NOT_MOUNTED'
        
        return filepath
    
    
    def load_selection(input_path, JOIN_SEL, exclude_list=exclude_list):
        """
        Loads the selection and returns a list of ids and count.
        """
        ## Load selection footprint
        selection = gpd.read_file(input_path)
        selection_count = len(selection)
        if exclude_list:
            with open(exclude_list, 'r') as el:
                exclude_ids = el.readlines()
                exclude_ids = [ei.strip('\n') for ei in exclude_ids]
                logger.debug('Excluding IDs:\n{}'.format('\n'.join(exclude_ids)))
            selection = selection[~selection[JOIN_SEL].isin(exclude_ids)]
        selection_unique_ids = list(selection[JOIN_SEL].unique())
        selection_unique_ids_str = str(selection_unique_ids).replace('[', '').replace(']', '')
    
        return selection_unique_ids_str, selection_count
    
    
    
    def load_table(FP, JOIN_FP, selection_unique_ids_str,
                   SERIES, SERIES_BOTH, SERIES_FIELD):
        ## Load aerial source table
        # Build where clause, including selecting only ids in selection
        where = "(sde.{}.{} IN ({}))".format(FP, JOIN_FP, selection_unique_ids_str)
        # Add series if only medium or high is desired, else add nothing and load both
        if SERIES != SERIES_BOTH:
            where += " AND (sde.{}.{} = '{}')".format(FP, SERIES_FIELD, SERIES)
        aia = query_footprint(FP, db=DB, table=True, where=where)
        
        return aia
    
    
    ## TODO: Add support for FLIGHTLINES selection inputs
    ## Determine type of selection input
    #selection_fields = list(selection)
    #if "PHOTO_ID" in selection_fields:
    #    selection_type = PHOTO_EXTENTS
    #else:
    #    selection_type = FLIGHTLINES
    
    ## Check arguments
    if not source_loc == FROM_DRIVE or source_loc == FROM_SERVER:
        logger.error('''Invalid "source_loc" argument. 
                            Must be one of {} or {}'''.format(FROM_DRIVE, FROM_SERVER))
        raise ValueError()
    if not os.path.exists(selection):
        logger.error('''Selection path does not exist.\n{}'''.format(selection))
        raise ValueError()
    
    if not os.path.exists(destination) and not os.path.isdir(destination):
        logger.error('''Destination path does not exist or is not a directory,
                         please provide an existing directory.\n{}'''.format(destination))
        raise ValueError()
    if high_res is True and med_res is True:
        SERIES = SERIES_BOTH
    elif high_res is True:
        SERIES = SERIES_HIGH
    elif med_res is True:
        SERIES = SERIES_MED
    else:
        logger.error('Please specify one of high_resolution or med_resolution.')
        raise ValueError()
    
    
    ### Get drive paths
    ## Load input table and join to danco table to create filepaths
    selection_unique_ids_str, selection_count = load_selection(selection,
                                                               JOIN_SEL=JOIN_SEL)
    aia = load_table(FP, JOIN_FP, selection_unique_ids_str,
                     SERIES, SERIES_BOTH, SERIES_FIELD)
    
    
    #### Create source paths: if they existed on the drive and server
    # Convert unix path to os style -- only necessary/does anything for Windows
    aia[DRIVE_PATH] = aia[FILEPATH].apply(os.path.normpath)
    # Create a relative path for the destination directory, eg: 'high/ABxxxxROLL/xxxx.tif.gz
    aia[RELATIVE_PATH] = aia.apply(lambda x: create_relative_paths(x, FILENAME), axis=1)
    # Create the location the file would be at if it existed on the server
    aia[SERVER_PATH] = aia.apply(lambda x: os.path.join(SERVER_LOC, x[RELATIVE_PATH]), axis=1)
    
    
    #### Create destination path 
    # Create full destination path
    aia[DST_PATH] = aia.apply(lambda x: os.path.join(destination, x[RELATIVE_PATH]), axis=1)
    # Check if destination exists
    aia[DST_EXISTS] = aia[DST_PATH].apply(lambda x: os.path.exists(x))
    

    if source_loc == FROM_DRIVE:
        ## Get all active drives to use in check for files mounted on drives
        active_drives = get_active_drives()
        active_drives = [d for d in active_drives if os.path.ismount(d)]
#        ## Get letters of mounted aerial imagery drives
#        # first level subdirectories on drives are './hsm' or './AHAP Tif files'
#        aerial_imagery_subdirs = ['hsm{}'.format(x) for x in range(0,10)]
#        aerial_imagery_subdirs.append('hsm')
#        aerial_imagery_subdirs.append('AHAP Tif files')
#        # Check if either of the subdir patterns exist on all mounted drives to
#        # decide if the mounted drive is a drive containing AHAP, thus skipping
#        # C and other drives (..unless the above are at prefixes are at the root)
#        ahap_drives = [d for d in active_drives 
#                         if True in [os.path.exists(os.path.join(d, sd)) 
#                                     for sd in aerial_imagery_subdirs]]
        aia[MNT_PATH] = aia.apply(lambda x: find_drive_location(x, active_drives, DRIVE_PATH), axis=1)
        SRC_PATH = MNT_PATH
        ahap_drives = set(list(aia[SRC_DRIVE]))
        logger.debug('Drives containing AHAP imagery:\n{}'.format('\n'.join(ahap_drives)))
    elif source_loc == FROM_SERVER:
        aia[MNT_PATH] = aia.apply(lambda x: find_server_location(x, SERVER_PATH), axis=1)
        SRC_PATH = SERVER_PATH
    
    
    #### Selected files for copying:
    #### only files that have a valid source drive mounted 
    #### (n/a for FROM_SERVER -- all should be 'mounted', but this will skip missing)
    aia_mounted = copy.deepcopy(aia[aia[MNT_PATH]!=NOT_MOUNTED])
    aia_mounted = aia_mounted[aia_mounted[DST_EXISTS] == True]
    
    high_status = 'Located {}/{} {} from selection on {}...'.format(len(aia_mounted[aia_mounted[SERIES_FIELD.lower()]==SERIES_HIGH]),
                                                                   selection_count,
                                                                   SERIES_HIGH,
                                                                   source_loc)
    med_status = 'Located {}/{} {} from selection on {}...'.format(len(aia_mounted[aia_mounted[SERIES_FIELD.lower()]==SERIES_MED]),
                                                               selection_count,
                                                               SERIES_MED,
                                                               source_loc)
    
    # Print status messages
    if SERIES == SERIES_BOTH:
        logger.info(high_status)
        logger.info(med_status)
    elif SERIES == SERIES_HIGH:
        logger.info(high_status)
    elif SERIES == SERIES_MED:
        logger.info(med_status)
        
    ## If list drives, get src drive names, like 'USGS_s74'.
    ## These are labeled on the drives.
    ## Then exit
    if list_drives is True:
        src_drives = list(aia[SRC_DRIVE].unique())
        logger.info('Drives required for copying selection to\n{}:\n{}'.format(destination, '\n'.join(src_drives)))
        if list_missing_paths is True:
            for sd in src_drives:
                missing_paths = list(aia[aia[DST_EXISTS]==False][FILEPATH])
                logger.info('Drive: {}'.format(sd))
                logger.info('Missing paths:\n{}'.format('\n'.join(missing_paths)))
        sys.exit()
        
    
    ###  Do copying
    # Create file of already copied to be use for excluding in subsequent copying
    if write_copied:
        if os.path.exists(write_copied):
            wc_open_mode = 'a'
        else:
            wc_open_mode = 'w'
        wc = open(write_copied, wc_open_mode)
    
    ## Copy loop
    # progress bar setup
    manager = enlighten.get_manager()
    pbar = manager.counter(total=len(aia_mounted[SRC_PATH]), desc='Copying:', unit='files')
    for src, dst in zip(aia_mounted[SRC_PATH], aia_mounted[DST_PATH]):
        # Make directory tree if necessary
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            logger.debug('Making directories: \n{}'.format(dst_dir))
            os.makedirs(dst_dir)
        if not os.path.exists(dst):
            logger.info('Copying \n{} -> \n{}\n'.format(src, dst))
            if not dryrun:
                shutil.copyfile(src, dst)
                if write_copied:
                    wc.write(os.path.basename(src).split('.')[0])
                    wc.write('\n')
        else:
            logger.debug('Destination file already exists, skipping: \n{}\n{}'.format(src, dst))
        pbar.update()
    if write_copied:
        wc.close()
        
    logger.debug('Done')
    
    aia.to_excel(r'C:\temp\aia.xlsx')
    aia_mounted.to_excel(r'C:\temp\aia_mnt.xlsx')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('selection', type=os.path.abspath,
                        help='Path to selection shapefile from aerial imagery footprint.')
    parser.add_argument('-d', '--destination', type=os.path.abspath,
                        required=True,
                        help='Destination path to copy imagery to.')
    parser.add_argument('-s', '--source_loc', type=str,
                        help='Source to copy from, either "server" or "drives".')
    parser.add_argument('-hr', '--high_resolution', action='store_true',
                        help='''Flag to specify copying high-resolution series. 
                                Can be used in conjunction with -m''')
    parser.add_argument('-mr', '--medium_resolution', action='store_true',
                        help='''Flag to specify copying high-resolution series. 
                                Can be used in conjunction with -h''')
    parser.add_argument('-l', '--list_drives', action='store_true',
                        help='List offline drive names and exit.')
    parser.add_argument('--list_missing_paths', action='store_true',
                        help='List full paths to selection records not in destination.')
    parser.add_argument('-w', '--write_copied', type=str,
                        help='''Text file path to write file names as they are copied.
                                If file already exists, file names will be appended.''')
    parser.add_argument('-e', '--exclude_list', type=str,
                        help='''List of already copied files to exclude. This is can be
                                the "write_copied" list from above.''')
    parser.add_argument('--dryrun', action='store_true',
                        help='Print copy actions without copying.')
    parser.add_argument('-v', '--verbose', action='store_true')
    
    args = parser.parse_args()
    
    selection = args.selection
    destination = args.destination
    source_loc = args.source_loc
    high_res = args.high_resolution
    med_res = args.medium_resolution
    list_drives = args.list_drives
    list_missing_paths = args.list_missing_paths
    write_copied = args.write_copied
    exclude_list = args.exclude_list
    dryrun = args.dryrun
    verbose = args.verbose
    
    test = main(selection=selection,
                destination=destination,
                source_loc=source_loc,
                high_res=high_res,
                med_res=med_res,
                list_drives=list_drives,
                list_missing_paths=list_missing_paths,
                write_copied=write_copied,
                exclude_list=exclude_list,
                dryrun=dryrun,
                verbose=verbose)    
