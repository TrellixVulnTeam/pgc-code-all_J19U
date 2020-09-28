
import subprocess
from subprocess import PIPE


from misc_utils.logging_utils import create_logger


logger = create_logger(__name__, 'sh', 'INFO')


otb_max_ram_hint = 1024

def run_subprocess(command):
    proc = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    for line in iter(proc.stdout.readline, b''):  # replace '' with b'' for Python 3
        logger.info(line.decode())
    proc_err = ""
    for line in iter(proc.stderr.readline, b''):
        proc_err += line.decode()
    if proc_err:
        logger.info(proc_err)
    output, error = proc.communicate()
    logger.debug('Output: {}'.format(output.decode()))
    logger.debug('Err: {}'.format(error.decode()))

# otb_env_loc = r'C:\OSGeo4W64\OTB-6.6.1-Win64\OTB-6.6.1-Win64\otbenv.bat'
otb_env_loc = r"C:\OTB-7.1.0-Win64\OTB-7.1.0-Win64\otbenv.bat"

run_subprocess(otb_env_loc)
logger.info('Setting OTB_MAX_RAM_HINT={}'.format(otb_max_ram_hint))
run_subprocess('set OTB_MAX_RAM_HINT={}'.format(otb_max_ram_hint))
logger.info('OTB Max Ram:')
run_subprocess('echo %OTB_MAX_RAM_HINT%')
