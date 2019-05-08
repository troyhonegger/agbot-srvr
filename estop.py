#!/usr/bin/python

import subprocess
import os
import signal
import time

from lib import loghelper
from lib import multivator
from lib import speed_ctrl

def _processor_pid():
    try:
        # runs 'pidof processor.py' in a shell and returns the output (a list
        # of PIDs), or raises a CalledProcessError upon a nonzero exit code.
        return int(subprocess.check_output(['pidof', 'processor.py']).split()[0])
    except subprocess.CalledProcessError:
        return None

def estop(kill_processor = False, new_process = False):
    if new_process:
        subprocess.Popen('/home/agbot/agbot-srvr/estop.py')
        return
    log = loghelper.get_logger(__file__)
    log.critical('Estop engaging: kill_processor=%s'%(kill_processor))
    pid = None
    if kill_processor:
        pid = _processor_pid()
        if pid is not None:
            # first, we politely ask processor.py to stop
            os.kill(pid, signal.SIGINT)
    try:
        multivator.Multivator().estop()
    except multivator.MultivatorException as ex:
        log.critical("Multivator estop FAILED: '%s'", repr(ex))
    try:
        speed_ctrl.SpeedController().estop()
    except speed_ctrl.SpeedControlException as ex:
        log.critical("Speed control estop FAILED: '%s'", repr(ex))
    
    if pid is not None and _processor_pid() is not None:
        log.critical("Processor.py still hasn't responded. Giving it a few more milliseconds...")
        time.sleep(0.2)
        if _processor_pid is not None:
            log.critical('Sending SIGKILL to processor - things are about to get ugly.')
            os.kill(pid, signal.SIGKILL)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--kill-processor', action = 'store_true', default = False)
    args = parser.parse_args()
    # new_process MUST be False here; otherwise an infinite loop of process creation will result
    estop(args.kill_processor, new_process = False)