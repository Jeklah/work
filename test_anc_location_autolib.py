"""
Tests that validate the insertion of SMPTE ST 352 Payload Identification Code Ancillary Data Packets
from the Qx/QxL.
"""

import logging
import os
# from pathlib import Path

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import Qx, TemporaryPreset
from autolib.logconfig import autolib_log
from autolib.testexception import TestException

log = logging.getLogger(autolib_log)

@pytest.fixture
def get_qx_hostname() -> str:
    """
    Returns the hostname of the Qx/QxL under test.
    """
    yield os.getenv("QX_HOSTNAME", None)


@pytest.fixture
def qx_unit(test_qx_hostname) -> Qx:
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname fixture.
    """
    qx = make_qx(test_qx_hostname)
    # print(f'{__file__}') 
    # print(f'{__name__}')
    module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
    preset_file = f'{module_path}{os.path.sep}_{type(qx).__name__}_basic_test.json'
    print(f'{module_path}')
    print(f'{preset_file}')
    #if not os.path.exists(preset_file):
    #    Path(preset_file).touch()

    # The TemporaryPreset context manager handles upload, activation and eventual
    # deletion of the presets to the Qx/QxL.
    with TemporaryPreset(qx, preset_file, "basic_test"):

        # The preset will be uploaded to the device and activated. Here before we 
        # yield the object we can set additional preconditions on the unit.
        # Let's turn off the bouncing box.
        original_bbox_state = qx.generator.bouncing_box
        qx.generator.bouncing_box = False
        # qx.generator.output_copy = False
        # qx.input_output.sdi_output = SDIIOType.BNC
        # qx.input_output.SDIOutputSource = SDIOutputSource.GENERATOR
        # log.info(f'FIXTURE: Generator Qx {qx.hostname} setup complete.')
        yield qx
        # Fixtures are generator functions so after test has run any teardown can be
        # performed here.
        # Let's restore the bouncing box state.
        qx.generator.bouncing_box = original_bbox_state
        # log.info(f'FIXTURE: Generator Qx {qx.hostname} teardown complete.')

    # The TemporaryPreset context manager will delete the preset from the Qx/QxL.


@pytest.fixture
def config():
    """
    Pytest fixture that will return a dictionary of configuration settings for tests to use.
    """

    # Here we could get configuration from a database, a static file or
    # (as with the below example) from an environment variable set by 
    # the CI/CD pipeline.

    expected_version = os.getenv("EXPECTED_VERSION", None)
    if not expected_version:
        raise TestException("Please ensure the environment variable EXPECTED_VERSION is set.")

    yield {
            'expected_version': expected_version
    }


class TestExampleSuite:
    """
    Tests may be module scope functions of class methods.
    Classes give a good way of grouping related tests and fixtures can be configured
    to be created at the start of each test function or once per class
    (there are additional scopes. Please see https://docs.pytest.org/en/stable/fixture.html).

    This test needs to be able to work on Qx/QxL units that are pre and post combined
    SDI / SDI stress mode, so operation mode is set using request_capability().
    """

    @pytest.mark.sdi
    def test_sdi_operation_mode(self, qx_unit, config):
        """
        * Switch the Qx / QxL to SDI mode.
        * Check the about box reported version number.
        * Generate 1080p59.94 YCbCr:422:10, 3G_A_Rec.709 with 100% Bars.
        """
        self._sdi_workload(qx_unit, OperationMode.SDI, config['expected_version'])


    @pytest.mark.sdi_stress
    def test_sdi_stress_operation_mode(self, qx_unit, config):
        """
        Place the test device in SDI Stress Toolkit mode and run a set of fundamental
        tests.
        """
        self._sdi_workload(qx_unit, OperationMode.SDI_STRESS, config['expected_version'])


    def _sdi_workload(self, test_qx, op_mode, expected_version):
        """
        Generalised SDI smoke test parametrerised for execution against different
        standards and test patterns. Note that this is not a test but rather an
        underscore ('private') method that should only be called from within
        this class. As a result, we do not list any fixtures in the parameter list.

        :param test_qx: Qx or QxL to perform test on.
        :param op_mode: OperationMode to use for the test (SDI or SDI_STRESS).
        """

        test_pattern = '100% Bars'
        res = '1920x1080p50'
        colour = 'YCbCr:422:10'
        gamut = '3G_A_Rec.709'

        # Set the operation mode and await completion.
        log.info(f'Starting test on {test_qx.hostname} - requesting capability {op_mode}')
        test_qx.request_capability(op_mode)

        # Check the reported version number
        assert Qx.RestOperationModeMap[test_qx.about["Software_version"]] == expected_version

        # Check that the four SDI BNC outputs are wired back to the four BNC inputs.
        test_qx.io.sdi_input_source = SDIIOType.BNC
        test_qx.io.sdi_output_source = SDIIOType.BNC
        test_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))

        # Start generator
        log.info(f'Setting generator to {res} - {colour} - {gamut} - {test_pattern}')
        test_qx.generator.set_generator(res, colour, gamut, test_pattern)
        assert test_qx.generator.is_generating_standard(res, colour, gamut, test_pattern)

        # Check analyser format matches the generator standard.
        assert test_qx.analyser.get_analyser_status() == (res, colour, gamut)
