# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 13:49:34 2019

@author: disbr007
Copies aerial imagery from offline drives or server to specified destination.
"""

import argparse
import copy
import platform
import os
import shutil
import sys

import geopandas as gpd
# from tqdm import tqdm
# import enlighten

from selection_utils.query_danco import query_footprint
from misc_utils.id_parse_utils import read_ids
from misc_utils.logging_utils import create_logger


### Inputs
#selection_p = r'E:\disbr007\UserServicesRequests\Projects\jclark\3948\ahap\selected_ahap_photo_extents.shp'
#dst_dir = r'C:\temp\ahap'
#src_loc = 'drives'
#SERIES = 'both' #'both' # 'high_res', 'medium_res'


def main(selection, destination, source_loc, high_res, med_res, tm,
         list_drives, list_missing_paths, write_copied, 
         write_footprint, exclude_list, dryrun, verbose):
    
    #### Logging setup
    if verbose == False:
        log_level = 'INFO'
    else:
        log_level = 'DEBUG'
    logger = create_logger('ahap_copier.py', 'sh',
                           handler_level=log_level)
    
    
    ## Params
    if platform.system() == 'Windows':
        SERVER_LOC = os.path.normpath(r'V:\pgc\data\aerial\usgs\ahap\photos')
    elif platform.system() == 'Linux':
        SERVER_LOC = os.path.normpath(r'/mnt/pgc/data/aerial/usgs/ahap/photos')
    PHOTO_EXTENTS = 'Photo_Extents'
    FLIGHTLINES = 'Flightlines'
    CAMPAIGN = 'AHAP'
    JOIN_SEL = 'PHOTO_ID'
    JOIN_FP = 'unique_id'
    FP = 'usgs_index_aerial_image_archive'
    DB = 'imagery'
    FILEPATH = 'filepath'
    FILENAME = 'filename'
    SRC_DRIVE = 'src_drive'
    SERIES_FIELD = 'series'
    SERIES_BOTH = 'both'
    SERIES_HIGH = 'high_res'
    SERIES_MED = 'medium_res'
    # Path to footprints -- used for writing footprint only
    FOOTPRINT_LOC = r'E:\disbr007\general\aerial\AHAP\AHAP_Photo_Extents\AHAP_Photo_Extents.shp'
    
    
    DRIVE_PATH = 'drive_path'
    MNT_PATH = 'mounted_path'

    RELATIVE_PATH = 'relative_path'
    SERVER_PATH = 'server_path'
    FROM_DRIVE = 'drives'
    FROM_SERVER = 'server'
    if source_loc == FROM_DRIVE:
        NOT_MOUNTED = 'NOT_MOUNTED'
    elif source_loc == FROM_SERVER:
        NOT_MOUNTED = 'NOT_ON_SERVER'
    DST_PATH = 'dst'
    DST_EXISTS = 'dst_exists'
    SRC_PATH = 'src'

    # transfer methods
    tm_copy = 'copy'
    tm_link = 'link'
    
        
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
            filepath = NOT_MOUNTED
        
        return filepath
    
    
    def load_selection(input_path, JOIN_SEL, exclude_list=exclude_list):
        """
        Loads the selection and returns a list of ids and count.
        """
        logger.info('Loading selection...')
        ## Load selection footprint
        if input_path.endswith('shp'):
            selection = gpd.read_file(input_path)
            # selection_count = len(selection)
            if exclude_list:
                with open(exclude_list, 'r') as el:
                    exclude_ids = el.readlines()
                    exclude_ids = [ei.strip('\n') for ei in exclude_ids]
                    logger.debug('Excluding IDs:\n{}'.format('\n'.join(exclude_ids)))
                selection = selection[~selection[JOIN_SEL].isin(exclude_ids)]
            selection_unique_ids = list(selection[JOIN_SEL].unique())
        elif input_path.endswith('txt'):
            selection_unique_ids = read_ids(input_path)

        selection_count = len(set(selection_unique_ids))
        logger.info('Scenes in selection: {:,}'.format(selection_count))
        selection_unique_ids_str = str(selection_unique_ids).replace('[', '').replace(']', '')
    
        return selection_unique_ids_str, selection_count
    
    
    
    def load_table(FP, JOIN_FP, selection_unique_ids_str,
                   SERIES, SERIES_BOTH, SERIES_FIELD):
        logger.debug('Loading danco AHAP table...')
        ## Load aerial source table
        # Build where clause, including selecting only ids in selection
        # where = "(sde.{}.{} IN ({}))".format(FP, JOIN_FP, selection_unique_ids_str)
        where = "({}.{} IN ({}))".format(FP, JOIN_FP, selection_unique_ids_str)
        # Add series if only medium or high is desired, else add nothing and load both
        if SERIES != SERIES_BOTH:
            # where += " AND (sde.{}.{} = '{}')".format(FP, SERIES_FIELD, SERIES)
            where += " AND ({}.{} = '{}')".format(FP, SERIES_FIELD, SERIES)
        aia = query_footprint(FP, db=DB, table=True, where=where)
        aia_ct = len(aia)
        logger.info('Records loaded in AHAP table: {:,}'.format(aia_ct))
        # Remove duplicates - there are identical records, but on different src_drives
        # Mainly seen on src_drives: USGS_s31 and USGS_s71
        # If this actually removes anything, a debug message will be logged.
        # TODO: Add option to keep all locations, only useful for copying from drives
        #       as there should be one of each file on the server
        aia = aia.drop_duplicates(subset=JOIN_FP)
        aia_dd = len(aia)
        if aia_dd != aia_ct:
            logger.debug('Duplicates dropped, identical records on multiples drives.')

        return aia
    
    
    ## TODO: Add support for FLIGHTLINES selection inputs
    ## Determine type of selection input
    #selection_fields = list(selection)
    #if "PHOTO_ID" in selection_fields:
    #    selection_type = PHOTO_EXTENTS
    #else:
    #    selection_type = FLIGHTLINES
    
    ## Check arguments
    if source_loc != FROM_DRIVE and source_loc != FROM_SERVER:
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
        aia[MNT_PATH] = aia.apply(lambda x: find_server_location(x), axis=1)
        SRC_PATH = SERVER_PATH
    
    
    #### Selected files for copying:
    #### only files that have a valid source drive mounted 
    #### (n/a for FROM_SERVER -- all should be 'mounted', but this will skip missing)
    aia_mounted = copy.deepcopy(aia[aia[MNT_PATH]!=NOT_MOUNTED])
    # aia_mounted = aia_mounted[aia_mounted[DST_EXISTS] == True]
    
    high_status = 'Located {:,}/{:,} {} from selection on {}...'.format(len(aia_mounted[aia_mounted[SERIES_FIELD.lower()]==SERIES_HIGH]),
                                                                   selection_count,
                                                                   SERIES_HIGH,
                                                                   source_loc)
    med_status = 'Located {:,}/{:,} {} from selection on {}...'.format(len(aia_mounted[aia_mounted[SERIES_FIELD.lower()]==SERIES_MED]),
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
    # manager = enlighten.get_manager()
    # pbar = manager.counter(total=len(aia_mounted[SRC_PATH]), desc='Copying:', unit='files')
    logger.info('Copying files from {} to {}...'.format(source_loc, destination))
    for src, dst in zip(aia_mounted[SRC_PATH], aia_mounted[DST_PATH]):
        # Make directory tree if necessary
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            logger.debug('Making directories: \n{}'.format(dst_dir))
            os.makedirs(dst_dir)
        if not os.path.exists(dst):
            logger.debug('Copying \n{} -> \n{}\n'.format(src, dst))
            if not dryrun:
                if tm == tm_copy:
                    shutil.copyfile(src, dst)
                elif tm == tm_link:
                    os.symlink(src, dst)
                if write_copied:
                    wc.write(os.path.basename(src).split('.')[0])
                    wc.write('\n')
        else:
            logger.debug('Destination file already exists, skipping: \n{}\n{}'.format(src, dst))
        # pbar.update()
    if write_copied:
        wc.close()

    if write_footprint:
        logger.info('Writing footprints...')
        aia_footprints = gpd.read_file(FOOTPRINT_LOC)
        aia_mounted = aia_mounted[['unique_id', 'campaign', 'series', 'filename',
                                   'flightline', 'file_sz_mb', 'photo_id', 
                                   'relative_path', ]]
        aia_footprints = aia_footprints.merge(aia_mounted, left_on='PHOTO_ID',
                                              right_on='unique_id', how='inner')
        aia_footprints.to_file(write_footprint)
    
    logger.debug('Done')


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
                                CANNOT be used in conjunction with -mr''')
    parser.add_argument('-mr', '--medium_resolution', action='store_true',
                        help='''Flag to specify copying high-resolution series. 
                                CANNOT be used in conjunction with -hr''')
    parser.add_argument('-tm', '--transfer_method', choices=['copy', 'link'],
                        default='link',
                        help='Method to use for transfering files.')
    parser.add_argument('-l', '--list_drives', action='store_true',
                        help='List offline drive names and exit.')
    parser.add_argument('--list_missing_paths', action='store_true',
                        help='List full paths to selection records not in destination.')
    parser.add_argument('-w', '--write_copied', type=str,
                        help='''Text file path to write file names as they are copied.
                                If file already exists, file names will be appended.''')
    parser.add_argument('-wf', '--write_footprint', type=os.path.abspath,
                        help='Write footprints of selected imagery.')
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
    write_footprint = args.write_footprint
    exclude_list = args.exclude_list
    tm = args.transfer_method
    dryrun = args.dryrun
    verbose = args.verbose
    
    main(selection=selection,
         destination=destination,
         source_loc=source_loc,
         high_res=high_res,
         med_res=med_res,
         tm=tm,
         list_drives=list_drives,
         list_missing_paths=list_missing_paths,
         write_copied=write_copied,
         write_footprint=write_footprint,
         exclude_list=exclude_list,
         dryrun=dryrun,
         verbose=verbose)    
