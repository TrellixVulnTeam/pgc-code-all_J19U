import argparse
import os
from pathlib import Path
import shutil
import time

from tqdm import tqdm

from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')


def sync_folders(src_dir, dst_dir, mod_date=True, dryrun=False):
    logger.info('Finding directory differences...')
    logger.info('Source 1:      {}'.format(src_dir))
    logger.info('Destination 2: {}'.format(dst_dir))
    copy_list = []
    for root, dirs, files in os.walk(src_dir):
        r = Path(root)
        pbar = tqdm(files)
        prev_dir = ''
        for f in pbar:
            fp = r / f
            cur_dir = fp.parent
            if cur_dir != prev_dir:
                pbar.write('Scanning: {}'.format(cur_dir.relative_to(src_dir)))
            rp = fp.relative_to(src_dir)
            dst = dst_dir / rp
            if not dst.exists():
                copy_list.append((fp, dst))
            elif mod_date and (os.path.getmtime(fp) > os.path.getmtime(dst)):
                copy_list.append((fp, dst))
            prev_dir = cur_dir
    logger.info('Differences found: {:,}'.format(len(copy_list)))
    time.sleep(5)

    logger.info('Syncing files...')
    if not dryrun:
        error_files = []
        pbar = tqdm(copy_list)
        for src, dst in pbar:
            if not dst.parent.exists():
                os.makedirs(dst.parent)
            pbar.write('Copying to: {}'.format(dst))
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                logger.error('Error copying file: {}'.format(src))
                logger.error(e)
                error_files = []
    if len(error_files) > 0:
        logger.warning('Errors during file copy: {}'.format(len(error_files)))
        logger.debug('Error files:\n{}'.format('\n'.join(error_files)))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Sync files between two folders.")

    parser.add_argument('-d1', '--directory1', type=os.path.abspath,
                        help='First directory (source directory if reverse=False.')
    parser.add_argument('-d2', '--directory2', type=os.path.abspath,
                        help='Second directory (destination if reverse=False.')
    parser.add_argument('--mod_date', action='store_true',
                        help='Check the modification date of files and sync if '
                             'newer version is found.')
    parser.add_argument('--reverse', action='store_true',
                        help='Also sync directory2 to directory1.')
    parser.add_argument('--dryrun', action='store_true',
                        help='Locate differences but do not sync.')

    args = parser.parse_args()

    sync_folders(src_dir=args.directory1, dst_dir=args.directory2,
                 mod_date=args.mod_date,
                 dryrun=args.dryrun)

    if args.reverse:
        sync_folders(src_dir=args.directory2, dst_dir=args.directory1,
                     mod_date=mod_date,
                     dryrun=args.dryrun)

    logger.info('Done.')
