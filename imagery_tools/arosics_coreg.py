import argparse
import os
from pathlib import Path
import pathlib
import warnings

import arosics

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

warnings.filterwarnings("ignore", message="You will likely lose important "
                                          "projection information when "
                                          "converting ")


def add_suffix(path, suffix):
    # TODO: Move to a "lib" module
    with_suffix = path.parent / '{}{}{}'.format(path.stem, suffix, path.suffix)
    return with_suffix


def make_paths(*path_strs):
    # TODO: Move to a "lib" module
    out_paths = []
    for p in path_strs:
        out_paths.append(Path(p))

    return out_paths


def img_coreg(im_ref: pathlib.PurePath, im_tar: pathlib.PurePath,
              out_dir=None, suffix='_cr_global',
              method='global', window_size=(256,256),
              max_shift=25, max_iter=5, local_grid_res=200,
              others=None, **kwargs):
    """Apply global coregistration to im_tar to align with im_ref. Optionally
    apply the same shift to others.
    kwargs arguments to COREG:
        fmt_out(str) – raster file format for output file. ignored if path_out is None.
            can be any GDAL compatible raster file format (e.g. ‘ENVI’, ‘GTIFF’; default: ENVI).
            Refer to http://www.gdal.org/formats_list.html to get a full list of supported formats.
        out_crea_options(list) – GDAL creation options for the output image,
            e.g. [“QUALITY=80”, “REVERSIBLE=YES”, “WRITE_METADATA=YES”]
        r_b4match(int) – band of reference image to be used for matching
            (starts with 1; default: 1)
        s_b4match(int) – band of shift image to be used for matching
            (starts with 1; default: 1)
        wp(tuple) – custom matching window position as map values in the same projection
            like the reference image (default: central position of image overlap)
        ws(tuple) – custom matching window size [pixels] (default: (256,256))
        max_iter(int) – maximum number of iterations for matching (default: 5)
        max_shift(int) – maximum shift distance in reference image pixel units (default: 5 px)
        align_grids(bool) – align the coordinate grids of the image to be and the reference image
            (default: 0)
        match_gsd(bool) – match the output pixel size to pixel size of the reference image
            (default: 0)
        out_gsd(tuple) – xgsd ygsd: set the output pixel size in map units
            (default: original pixel size of the image to be shifted)
        target_xyGrid(list) – a list with a target x-grid and a target y-grid like
            [[15,45], [15,45]] This overrides ‘out_gsd’, ‘align_grids’ and ‘match_gsd’."""

    if not out_dir:
        out_dir = os.path.dirname(im_tar)

    # Ensure all paths are pathlib.Paths
    im_ref, im_tar, out_dir, *others = make_paths(im_ref, im_tar, out_dir, *others)

    # Coregistration
    tar_out = add_suffix(out_dir / im_tar.name, suffix)
    logger.info('Reference:   {}'.format(im_ref))
    logger.info('Target:      {}'.format(im_tar))
    logger.info('Destination: {}'.format(tar_out))
    logger.info('Determining shifts...')
    if method == 'global':
        cr = arosics.COREG(str(im_ref), str(im_tar), ws=window_size,
                           max_shift=max_shift, max_iter=max_iter,
                           path_out=str(tar_out), **kwargs)
        logger.info('Applying shifts...')
        cr.correct_shifts()

        shifts_px = cr.coreg_info['corrected_shifts_px']
        shifts_map = cr.coreg_info['corrected_shifts_map']
        logger.info('Shift reliability: {}'.format(cr.shift_reliability))
        logger.info('Shift results (px) : {}'.format(shifts_px))
        logger.info('Shift results (map): {}'.format(shifts_map))

    elif method == 'local':
        cr = arosics.COREG_LOCAL(str(im_ref), str(im_tar), window_size=window_size,
                           max_shift=max_shift, max_iter=max_iter, grid_res=local_grid_res,
                           path_out=str(tar_out), **kwargs)
        logger.info('Applying shifts...')
        cr.correct_shifts()

        shifts_px = cr.coreg_info['mean_shifts_px']
        shifts_map = cr.coreg_info['mean_shifts_map']
        logger.info('Shift results (avg) (px) : {}'.format(shifts_px))
        logger.info('Shift results (avg) (map): {}'.format(shifts_map))

    if others:
        for o in others:
            logger.info('Applying same shift to: {}'.format(o))
            o_out = add_suffix(out_dir / o.name, suffix)
            other_ds = arosics.DESHIFTER(str(o),
                                         cr.coreg_info,
                                         path_out=str(o_out)).correct_shifts()

    return cr


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-ref', '--reference_image', type=os.path.abspath,
                        help='Reference image to register target to.')
    parser.add_argument('-tar', '--target_image', type=os.path.abspath,
                        help='Target image to be registered.')
    parser.add_argument('-m', '--method', type=str, choices=['global', 'local'],
                        default='global',
                        help='Type of coregistration to use. '
                             'Global is a constant x/y shift.'
                             'Local is grid of spatial shifts.')
    parser.add_argument('-sfx', '--suffix', type=str,
                        help='Suffix to append to target filename.')
    parser.add_argument('-od', '--out_directory', type=os.path.abspath,
                        help='Directory to write registered image(s) to. Default '
                             'is target_image directory.')
    parser.add_argument('--local_grid_res', type=int, default=200,
                        help='Tie-point grid resolution in pixels.')
    parser.add_argument('--window_size', type=int, nargs=2, default=[256, 256],
                        help='Size of window to compute coregistration within, in pixels.')
    parser.add_argument('--max_shift', type=float, default=25,
                        help='Maximum shift to allow as valid, in pixels.')
    parser.add_argument('--max_iter', type=int, default=5,
                        help='Maximum number of iterations for matching.')
    parser.add_argument('--others', type=os.path.abspath, nargs='+', default=[],
                        help='Other files to apply the same shift to.')

    args = parser.parse_args()

    im_ref = Path(args.reference_image)
    im_tar = Path(args.target_image)
    coreg_method = args.method
    suffix = args.suffix
    out_directory = Path(args.out_directory)
    local_grid_res = args.local_grid_res
    window_size = tuple(args.window_size)
    max_shift = args.max_shift
    max_iter = args.max_iter
    others = [Path(o) for o in args.others]

    img_coreg(im_ref, im_tar, method=coreg_method, suffix=suffix,
              local_grid_res=local_grid_res, out_dir=out_directory,
              window_size=window_size, max_shift=max_shift, max_iter=max_iter,
              others=others)
