import os, string, sys, re, glob, argparse, subprocess, logging
from osgeo import gdal, gdalconst
from lib import taskhandler

#### Create Logger
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)

task_abrv = 'rgb2pan'

default_qsub = 'qsub_rgb2pan.sh'
default_res = 16
default_format = 'GTIFF'
default_suffix = '_pan'
suffixes = ('ortho', 'matchtag', 'ms_img')
formats = ('JPEG', 'GTiff')


def main():
    parser = argparse.ArgumentParser()

    #### Set Up Options
    parser.add_argument("srcdir", help="source directory or image")
    parser.add_argument("--dstdir", help="destination directory")
    parser.add_argument("--dst_suffix", default=default_suffix,
                        help="Suffix to add to destination files.")
    parser.add_argument("--rgb_order", nargs=3, default=[3, 2, 1],
                        help='Red, green, blue band numbers, e.g.: 3 2 1')
    parser.add_argument('--src_suffix', help='Filename suffix to match when '
                                             'searching for files, including extension. '
                                             'E.g.: MS.tif')
    parser.add_argument("-r", "--resolution", default=default_res, type=int,
                        help="output resolution (default={})".format(default_res))
    parser.add_argument("-f", "--format", default='JPEG', choices=formats,
                        help="output format (default={})".format(default_format))
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing files if present")
    parser.add_argument("--pbs", action='store_true', default=False,
                        help="submit tasks to PBS")
    parser.add_argument("--parallel-processes", type=int, default=1,
                        help="number of parallel processes to spawn (default 1)")
    parser.add_argument("--qsubscript",
                        help="qsub script to use in PBS submission (default is qsub_rgb2pan.sh in script root folder)")
    parser.add_argument("--dryrun", action="store_true", default=False,
                        help="print actions without executing")
    pos_arg_keys = ['srcdir']

    #### Parse Arguments
    args = parser.parse_args()
    scriptpath = os.path.abspath(sys.argv[0])
    path = os.path.abspath(args.srcdir)

    #### Validate Required Arguments
    if not os.path.isdir(path) and not os.path.isfile(path):
        parser.error('src must be a valid directory or file')

    ## Verify qsubscript
    if args.qsubscript is None:
        qsubpath = os.path.join(os.path.dirname(scriptpath), default_qsub)
    else:
        qsubpath = os.path.abspath(args.qsubscript)
    if not os.path.exists(qsubpath):
        parser.error("qsub script path is not valid: %s" % qsubpath)

    ## Verify processing options do not conflict
    if args.pbs and args.parallel_processes > 1:
        parser.error("Options --pbs and --parallel-processes > 1 are mutually exclusive")

    #### Set up console logging handler
    lso = logging.StreamHandler()
    lso.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s- %(message)s', '%m-%d-%Y %H:%M:%S')
    lso.setFormatter(formatter)
    logger.addHandler(lso)

    #### Get args ready to pass to task handler
    arg_keys_to_remove = ('qsubscript', 'dryrun', 'pbs', 'parallel_processes')
    arg_str_base = taskhandler.convert_optional_args_to_string(args, pos_arg_keys, arg_keys_to_remove)

    # Determine extension based on format
    ext = get_extension(args.format)

    task_queue = []
    i = 0
    logger.info("Searching for imagery matching suffix...")
    # This operates on a single file
    if os.path.isfile(path):
        if path.endswith(args.src_suffix):
            # multispectral image file
            ms_img = path
            if args.dstdir:
                pan_img = os.path.join(args.dstdir, "{}{}.{}".format(
                    os.path.basename(os.path.splitext(ms_img)[0]),
                    args.dst_suffix,
                    ext))
            else:
                pan_img = "{}{}.{}".format(os.path.splitext(ms_img)[0],
                                           args.dst_suffix,
                                           ext)
            if not os.path.exists(pan_img) or args.overwrite:
                i += 1
                task = taskhandler.Task(
                    os.path.basename(ms_img),
                    '{}{:04g}'.format(task_abrv, i),
                    'python',
                    '{} {} {}'.format(scriptpath, arg_str_base, ms_img), # TODO: Finalize args
                    rgb2pan,
                    [ms_img, args]
                )
                task_queue.append(task)

    # This searches a directory
    else:
        for root, dirs, files in os.walk(path):
            for f in files:
                if f.endswith(args.src_suffix):
                    ms_img = os.path.join(root, f)
                    if args.dstdir:
                        pan_img = os.path.join(args.dstdir,
                                               "{}{}.{}".format(
                                                   os.path.basename(os.path.splitext(ms_img)[0]),
                                                   args.dst_suffix,
                                                   ext))
                    else:
                        pan_img = "{}{}.{}".format(os.path.splitext(ms_img)[0],
                                                   args.dst_suffix,
                                                   ext)
                    if not os.path.exists(pan_img) or args.overwrite:
                        i += 1
                        task = taskhandler.Task( # TODO: Copy from above
                            f,
                            'Browse{:04g}'.format(i),
                            'python',
                            '{} {} {}'.format(scriptpath, arg_str_base, ms_img),
                            rgb2pan,
                            [ms_img, args]
                        )
                        task_queue.append(task)

    logger.info('Number of incomplete tasks: {}'.format(i))
    if len(task_queue) > 0:
        logger.info("Submitting Tasks")
        if args.pbs:
            task_handler = taskhandler.PBSTaskHandler(qsubpath)
            if not args.dryrun:
                task_handler.run_tasks(task_queue)

        elif args.parallel_processes > 1:
            task_handler = taskhandler.ParallelTaskHandler(args.parallel_processes)
            logger.info("Number of child processes to spawn: {0}".format(task_handler.num_processes))
            if not args.dryrun:
                task_handler.run_tasks(task_queue)

        else:
            for task in task_queue:
                src, task_arg_obj = task.method_arg_list

                #### Set up processing log handler
                logfile = os.path.splitext(src)[0] + ".log"
                lfh = logging.FileHandler(logfile)
                lfh.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s %(levelname)s- %(message)s', '%m-%d-%Y %H:%M:%S')
                lfh.setFormatter(formatter)
                logger.addHandler(lfh)

                if not args.dryrun:
                    task.method(src, task_arg_obj)

                #### remove existing file handler
                logger.removeHandler(lfh)

    else:
        logger.info("No tasks found to process")


def rgb2pan(ms_img, args):
    ext = get_extension(args.format)
    r_band_num, g_band_num, b_band_num = args.rgb_order
    if args.dstdir:
        tempfile = "{}_temp.tif".format(os.path.join(args.dstdir, os.path.basename(os.path.splitext(ms_img)[0])))
        pan_img = os.path.join(args.dstdir, "{}{}.{}".format(
            os.path.basename(os.path.splitext(ms_img)[0]),
            args.dst_suffix,
            ext))
    else:
        tempfile = "{}_temp.tif".format(os.path.splitext(ms_img)[0])
        pan_img = "{}{}.{}".format(os.path.splitext(ms_img)[0],
                                   args.dst_suffix,
                                   ext)

    deletables = []
    deletables.append(tempfile)

    if not os.path.isfile(pan_img) or args.overwrite is True:
        logger.info("Converting to panchromatic: {}".format(ms_img))
        cmd = 'gdal_calc.py -A {0} --A_band={1} -B {0} --B_band={2} -C {0} --C_band={3} ' \
              '--outfile={4} --calc="A*0.2989+B*0.5870+C*0.1140"'.format(ms_img,
                                                                         r_band_num,
                                                                         g_band_num,
                                                                         b_band_num,
                                                                         pan_img)

        if not args.dryrun:
            taskhandler.exec_cmd(cmd)

        if not args.dryrun:
            for f in deletables:
                if os.path.isfile(f):
                    try:
                        os.remove(f)
                    except:
                        print
                        "Cannot remove %s" % f


def get_extension(image_format):
    if image_format == 'GTiff':
        return 'tif'
    elif image_format == 'JPEG':
        return 'jpg'


if __name__ == '__main__':
    main()

