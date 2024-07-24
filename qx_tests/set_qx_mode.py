#!/usr/bin/env python3
"""Change Qx / QxL operation mode.

Usage:
    set_qx_mode.py HOSTNAME MODE
    set_qx_mode.py --version

Arguments:
    HOSTNAME                Hostname of the Qx / QxL (e.g. qx-020000.phabrix.local)
    MODE                    "SDI", "SDI_STRESS", "IP_2110" or "IP_2022_6"

Options:
    -h, --help              Usage instructions
    --version               Show version and exit

"""

from docopt import docopt
from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode

if __name__ == "__main__":
    arguments = docopt(__doc__, version='0.0.1')
    # DocOpt ensures that the required parameters are supplied
    with make_qx(arguments['HOSTNAME']) as qx:
        # If any aspect of the upgrade fails, an exception will be thrown and this tool will return a non-zero error.
        op_mode = OperationMode.from_name(arguments['MODE'])
        if op_mode:
            qx.request_capability(op_mode)
        else:
            print(f"Mode must be SDI, SDI_STRESS, IP_2110 or IP_2022_6. {arguments['MODE']} is not supported.")
