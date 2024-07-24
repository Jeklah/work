"""
SDI operating mode smoke test regression tests. 

Tests in this module perform fundamental tests of the SDI functionality
of the Qx / QxL cover the most important SDI functionality and are used to aid assessment of whether further testing 
should be performed. If this suite fails developers should be informed immediately by the continuous integration system.
"""    

import logging
import os
import time

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType
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


class TestSDIModesSmoke:
    """
    This special test suite sets up the Qx for test runs, checking that the software can be updated, the operation mode
    set. There are two markers 'initial_setup' and 'smoke'. The 'initial_setup' tests should be run first by CI and
    are operation mode agnostic. The 'smoke' tests check basic functionality in the various operation modes and should
    be run before running the operation mode specific tests in the main suite.

    e.g.::

        pytest -v -m initial_install  # Run the initial upgrade and check
        pytest -v -m smoke -m sdi     # Run the SDI smoke test and leave the Qx in SDI mode
        pytest -v -m sdi -m "not smoke" -m "not initial_install"  # Run the complete SDI test suite

    If these tests fail, the main suite should not be run as it would be a waste of time and resources.

    """

    @pytest.mark.smoke
    @pytest.mark.sdi
    def test_sdi_operation_mode(self, qx):
        """
        Place the test device in SDI mode and run a set of fundamental tests.
        """
        module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
        qx.request_capability(OperationMode.SDI)
        self._sdi_workload(qx, OperationMode.SDI, f"{module_path}{os.path.sep}_{type(qx).__name__}_sdi_smoke_test.json")

    @pytest.mark.smoke
    @pytest.mark.sdi_stress
    def test_sdi_stress_operation_mode(self, qx):
        """
        Place the test device in SDI Stress Toolkit mode and run a set of fundamental tests.
        """
        module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
        qx.request_capability(OperationMode.SDI_STRESS)
        self._sdi_workload(qx, OperationMode.SDI_STRESS, f"{module_path}{os.path.sep}_{type(qx).__name__}_sdi_stress_smoke_test.json")

    def _sdi_workload(self, test_qx, op_mode, preset_file, test_pattern='100% Bars', res='1920x1080p50', colour='YCbCr:422:10', gamut='3G_A_Rec.709'):
        """
        Generalised SDI smoke test parameterised for execution against different standards and test patterns.

        :param test_qx: Qx or QxL to perform test on.
        :param op_mode: OperationMode to use for the test (SDI or SDI_STRESS)
        :param preset_file: Preset file to load onto the unit at the start of the test
        :param test_pattern: Test pattern name
        :param res: The resolution, format and frame rate identifier
        :param colour: The pixel format
        :param gamut: The data rate and colour gamut identifier.

        """
        log.info(f"Starting {'SDI' if op_mode == OperationMode.SDI else 'SDI Stress'} smoke test on {test_qx.hostname} - requesting capability: {op_mode}")
        test_qx.request_capability(op_mode)

        log.info(f"Uploading a preset {preset_file} as smoke_test_init on {test_qx.hostname}")
        with TemporaryPreset(test_qx, preset_file, "smoke_test_init"):
            assert test_qx.query_capability(op_mode)

            # Check that the four SDI BNC outputs are wired back to the four BNC inputs
            test_qx.io.sdi_input_source = SDIIOType.BNC
            test_qx.io.sdi_output_source = SDIIOType.BNC
            test_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))

            # Start generator
            log.info(f'Setting generator to {res} - {colour} - {gamut} - {test_pattern}')
            test_qx.generator.output_copy = False
            test_qx.generator.bouncing_box = False
            test_qx.generator.set_generator(res, colour, gamut, test_pattern)

            time.sleep(5)

            assert test_qx.generator.is_generating_standard(res, colour, gamut, test_pattern)

            # Clear all CRC input failure counters
            test_qx.analyser.reset_crc()

            # Check analyser format matches the generator standard.
            assert test_qx.analyser.get_analyser_status() == (res, colour, gamut)

            # Check for input errors
            crc_summary = test_qx.analyser.get_crc_summary()
            assert crc_summary.get('errorCount', None) == 0
            assert crc_summary.get('inputFailures', None) == 0

            # Check CRC 10 times over 10s to make sure bouncing box is not onscreen
            samples = []
            for sample in range(10):
                samples.append(test_qx.analyser.get_crc_analyser())
                time.sleep(1)

            # @DUNC Check the list you idiot.
