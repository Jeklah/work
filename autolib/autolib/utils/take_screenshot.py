#!/usr/bin/env python3
"""Take a screenshot of a Qx via the REST API.
Please ensure the REST API is enabled and the VNC server is disabled on the Qx.

Usage: 
    take_screenshot.py HOSTNAME
    take_screenshot.py --version

Arguments:
    HOSTNAME                Hostname of the Qx / QxL (e.g. qx-020123.phabrix.local)

Options:
    -h, --help              Usage instructions
    --version               Show version and exit

"""

from docopt import docopt
from pathlib import Path
import autolib
from autolib.factory import make_qx

if __name__ == "__main__":
    autolib.log_handler()
    arguments = docopt(__doc__, version='0.0.1')
    with make_qx(arguments.get('HOSTNAME', None)) as qx:
        screenshot_filename = qx.take_screenshot()
        if screenshot_filename:
            remote_name = Path('/transfer/screenshots') / screenshot_filename
            local_name = Path('.') / screenshot_filename
            qx.ssh.download_via_sftp(remote_name, local_name, 10)
            print(f"Downloaded screenshot as {local_name}")
        else:
            print(f"Unable to obtain screenshot from {arguments.get('HOSTNAME')}")
