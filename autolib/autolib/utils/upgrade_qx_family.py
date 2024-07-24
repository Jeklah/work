#!/usr/bin/env python3
"""Upgrade Qx or QxL firmware and software from a file.

Usage:
    upgrade_qx_family.py HOSTNAME FILENAME
    upgrade_qx_family.py --version

Arguments:
    HOSTNAME                Hostname of the Qx / QxL (e.g. qx-020123.phabrix.local)
    FILENAME                Filename and pathname of the installer to upload.

Options:
    -h, --help              Usage instructions
    --version               Show version and exit

"""

from docopt import docopt
from autolib.factory import make_qx

if __name__ == "__main__":
    arguments = docopt(__doc__, version='0.0.1')
    # DocOpt ensures that the required parameters are supplied
    with make_qx(arguments['HOSTNAME']) as qx:
        # If any aspect of the upgrade fails, an exception will be thrown and this tool will return a non-zero error.
        qx.upgrade(file=arguments['FILENAME'])
