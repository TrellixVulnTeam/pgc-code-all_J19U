# TODO: Currently taking a long time to process/potentially not working
import argparse
import os
import re
import subprocess
from subprocess import PIPE

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'INFO')

# Args
rasters = [r'V:\pgc\data\scratch\jeff\ms\2020sep25_her\img\ortho_selected\WV02_20110908214444_103001000D6F6600_11SEP08214444-M1BS-500060286060_01_P001_u16mr3413_pansh.tif']
nodata_val = 0
update = False


def run_subprocess(command, debug_filters=None, return_lines=None):
    """Run the commmand passed as a subprocess.
    Optionally use debug_filter to route specific messages from the
    subprocess to the debug logging level.
    Optionally matching specific messages and returning them.

    Parameters
    ----------
    command : str
        The command to run.
    debug_filters : list
        List of strings, where if any of the strings are in
        the subprocess message, the message will be routed to
        debug.
    return_lines : list
        List of tuples of (string, int) where the strings are
        regex patterns and int are group number within match to
        return.

    Returns
    ------
    return_lines : list / None
    """
    message_values = []
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        message = line.decode()
        if debug_filters:
            if any([f in message.lower() for f in debug_filters]):
                logger.debug(message)
            else:
                logger.info(message)
            if return_lines:
                for pattern, group_num in return_lines:
                    pat = re.compile(pattern)
                    match = pat.search(message)
                    if match:
                        value = match.group(group_num)
                        message_values.append(value)

    proc_err = ""
    for line in iter(proc.stderr.readline, b''):
        proc_err += line.decode()
    if proc_err:
        logger.info(proc_err)
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))

    return message_values


for r in rasters:
    o = r.replace('.tif', '_nd.tif')
    cmd = "gdal_translate -a_nodata {} {} {}".format(nodata_val, r, o)
    print(cmd)
    run_subprocess(cmd)