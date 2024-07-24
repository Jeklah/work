"""\
Another example test.
"""

import logging
import os

import pytest
from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.operationmode import OperationMode
from autolib.testexception import TestException

log = logging.getLogger(autolib_log)


@pytest.fixture(scope="session")
def qx_unit():
    hostname = os.getenv("TEST_QX_HOSTNAME", None)
    if not hostname:
        raise TestException("Please set environment variable TEST_QX_HOSTNAME to the test unit's hostname")
    qx = make_qx(hostname)

    # Now we have the qx object - any setup required can be performed here. The fixture's scope parameter will
    # determine when the setup code will be called (session scope, module scope, class scope, test scope). Here,
    # the session scope means that the fixture will be set up once the first time it is used in a test run.
    yield qx
    # Any code following the yield will be called when the fixture is destroyed. The timing of this will depend on
    # the fixture's defined scope. In this example, the code here following the yield will be run at the end of the
    # test run session.


@pytest.mark.slow
@pytest.mark.sdi
def test_operation_modes(qx_unit):
    """
    This test sets the Qx to SDI mode, then switches to 2110 and 2022-6 modes checking each mode is correctly set.
    """

    log.info(f'Starting test on {qx_unit.hostname}.')

    for mode in [OperationMode.IP_2110, OperationMode.IP_2022_6]:

        # Set the operating mode and await completion
        log.info(f'{qx_unit.hostname} is in {qx_unit.operation_mode} mode, setting operating mode to {mode}')

        # The setter changes the operation mode and blocks until it successfully completes.
        qx_unit.operation_mode = mode

        # If the change in operation mode fails, an appropriate exception is raised to indicate the error
        log.info(f'{qx_unit.hostname} is now {qx_unit.operation_mode} mode.')

        # Check the operation mode
        assert qx_unit.operation_mode == mode
