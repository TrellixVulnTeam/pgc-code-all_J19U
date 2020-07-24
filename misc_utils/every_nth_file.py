import os
import argparse
import logging
from itertools import groupby
import shutil

# src_dir = r'C:\temp'
# dst_dir = r'C:\temp\test'
# ext = None
# step = 2
# logfile = None

def main(args):
    src_dir = args.src_dir
    dst_dir = args.dst_dir
    step = args.step
    action = args.action
    groupby_first_n = args.groupby_first_n
    sort = args.sort
    ext = args.ext
    logfile = args.log
    verbose = args.verbose
    dryrun = args.dryrun


    if action == 'copy':
        verb_form = 'copying'
    elif action == 'move':
        verb_form = 'moving'
    elif action == 'delete':
        verb_form = 'deleting'

    # Logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    if verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if logfile:
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Get file contents
    contents = [os.path.join(src_dir, f) for f in os.listdir(src_dir)
                if os.path.isfile(os.path.join(src_dir, f))]
    if sort:
        contents = sorted(contents, )
    if ext:
        contents = [f for f in contents if f.endswith(ext)]
    if groupby_first_n:
        contents = [list(i) for j, i in groupby(contents, lambda x: os.path.basename(x)[0:groupby_first_n])]

    logger.info('Number of files (or groups) in source directory (matching extension if provided): {:,}'.format(len(contents)))

    # Get every nth file
    nth_files = []
    for i, f in enumerate(contents):
        if i % step == 0:
            nth_files.append(f)

    # Flatten if it was a groupby
    if groupby_first_n:
        nth_files = [f for sublist in nth_files for f in sublist]

    logger.info('Number of files to {}: {}'.format(action, len(nth_files)))
    logger.info('{}...'.format(verb_form))
    for i, f in enumerate(nth_files):
        logger.debug('{} file {:,}: {}'.format(verb_form, i, f))
        if not dryrun:
            try:
                if action == 'copy':
                    shutil.copy2(f, dst_dir)
                elif action == 'move':
                    shutil.move(f, dst_dir)
                elif action == 'delete':
                    os.remove(f)
            except Exception as e:
                logger.error('Failed to copy file: {}'.format(f))
                logger.error(e)

    logger.info('Done copying. Files in destination directory: {}'.format(len(os.listdir(dst_dir))))
    if dryrun:
        logger.info('(dryrun)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('src_dir', type=os.path.abspath,
                        help='Path to directory containing files to copy.' )
    parser.add_argument('dst_dir', type=os.path.abspath,
                        help='Path to directory to move/copy every nth file to. Irrelevent for "delete"')
    parser.add_argument('step', type=int,
                        help="""Interval at which to perform action on files. 
                                1 = action on every file. 2 = action on every other, etc.""")
    parser.add_argument('action', type=str, choices=['copy', 'move', 'delete'],
                        help='Action to perform on every nth item.')
    parser.add_argument('-g', '--groupby_first_n', type=int,
                        help="""Number of characters at start of filename to group by. Actions will
                                be performed on every nth group.""")
    parser.add_argument('-sort', action='store_true',
                        help='Sort files alphabetically before copying every nth.')
    parser.add_argument('-ext', type=str,
                        help='Move only files ending with provided string')
    parser.add_argument('-log', type=os.path.abspath,
                        help='File to log actions to. Will contain every file copied.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print details of every copy.')
    parser.add_argument('-d', '--dryrun', action='store_true', help="Print actions without copying.")
    
    args = parser.parse_args()

    main(args)
