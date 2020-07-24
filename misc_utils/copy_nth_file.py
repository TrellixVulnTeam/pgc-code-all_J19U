import os
import argparse
import logging
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
    sort = args.sort
    ext = args.ext
    logfile = args.log
    verbose = args.verbose
    dryrun = args.dryrun

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

    logger.info('Number of files in source directory (matching extension if provided): {:,}'.format(len(contents)))

    # Get every nth file
    keep_files = []
    for i, f in enumerate(contents):
        if i % step == 0:
            keep_files.append(f)

    logger.info('Number of files to copy: {}'.format(len(keep_files)))
    logger.info('Copying...')
    for i, f in enumerate(keep_files):
        logger.debug('Copying file {:,}: {}'.format(i, f))
        if not dryrun:
            try:
                shutil.copy2(f, dst_dir)
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
                        help='Path to directory to move every nth file to.')
    parser.add_argument('step', type=int,
                        help='Interval at which to move files. 1 = move every file. 2 = move every other, etc.')
    parser.add_argument('-sort', action='store_true',
                        help='Sort file alphabetically before copying every nth.')
    parser.add_argument('-ext', type=str,
                        help='Move only files ending with provided string')
    parser.add_argument('-log', type=os.path.abspath,
                        help='File to log actions to. Will contain every file copied.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print details of every copy.')
    parser.add_argument('-d', '--dryrun', action='store_true', help="Print actions without copying.")
    
    args = parser.parse_args()

    main(args)
