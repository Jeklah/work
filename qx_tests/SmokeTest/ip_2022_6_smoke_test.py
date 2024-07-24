"""
ST2022-6 operating mode smoke test regression tests. 

Tests in this module perform fundamental tests of the 2022-6 
functionality of the Qx / QxL cover the most important 2022-6 functionality and are used to aid assessment of whether 
further testing should be performed. If this suite fails developers should be informed immediately by the continuous 
integration system.
"""

import logging
import os

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import TemporaryPreset
from autolib.logconfig import autolib_log

log = logging.getLogger(autolib_log)


@pytest.fixture
def qx(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname global fixture.
    """
    qx = make_qx(test_qx_hostname)
    log.info(f"FIXTURE: Qx {qx.hostname} setup complete")
    yield qx
    log.info(f"FIXTURE: Qx {qx.hostname} teardown complete")


class TestIP20226Smoke:
    """
    This special test suite sets up the Qx for 2022-6 test runs, checking that the software can be updated, the
    operation mode set. There are two markers 'initial_setup' and 'smoke'. The 'initial_setup' tests should be run
    first by CI and are operation mode agnostic. The 'smoke' tests check basic functionality in the various operation
    modes and should be run before running the operation mode specific tests in the main suite.

    e.g.::

        pytest -v -m initial_install  # Run the initial upgrade and check
        pytest -v -m smoke -m ip2022_6     # Run the 2022-6 smoke test and leave the Qx in 2022-6 mode
        pytest -v -m ip2022_6 -m "not smoke" -m "not initial_install"  # Run the complete 2022-6 test suite

    If these tests fail, the main suite should not be run as it would be a waste of time and resources.

    """

    @pytest.mark.smoke
    @pytest.mark.ip2022_6
    def test_ip_2022_6_operation_mode(self, qx):
        """
        Place the test device in 2022-6 mode and run a set of fundamental tests.
        """
        module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
        qx.request_capability(OperationMode.IP_2022_6)
        self._ip_2022_6_workload(qx, OperationMode.IP_2022_6, f"{module_path}{os.path.sep}_{type(qx).__name__}_ip_2022_6_smoke_test.json")

    def _ip_2022_6_workload(self, test_qx, op_mode, preset_file, test_pattern='100% Bars', res='1920x1080p50', colour='YCbCr:422:10', gamut='3G_A_Rec.709'):
        """
        IP 2022-6 smoke test - tests basic 2022-6 functionality.

        :param test_qx: Qx or QxL to perform test on.
        :param op_mode: OperationMode to use for the test (IP_2022_6
        :param preset_file: Preset file to load onto the unit at the start of the test
        :param test_pattern: Test pattern name
        :param res: The resolution, format and frame rate identifier
        :param colour: The pixel format
        :param gamut: The data rate and colour gamut identifier.

        """
        log.info(f"Starting IP 2022-6 smoke test on {test_qx.hostname} - setting operating mode to {op_mode}")
        test_qx.request_capability(op_mode)

        log.info(f"Uploading a preset {preset_file} as smoke_test_init on {test_qx.hostname}")
        with TemporaryPreset(test_qx, preset_file, "smoke_test_init"):
            assert test_qx.query_capability(op_mode)

