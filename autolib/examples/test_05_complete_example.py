"""\
This is a more realistic test that demonstrates mode features of the Phabrix automation library. The fixture that
creates the Qx / QxL object that the test uses performs module level setup and teardown of the device in part through
the use of a temporary preset uploaded to the unit at the start of the tests (which is then removed after the tests
complete).

There is also a second fixture that's used to pass a dictionary of configuration settings into the tests. In this case
the fixture obtains a value from an environment variable (

Importantly, this test demonstrates how a test can be written such that there are subtly different versions for
different operating modes by moving the body of the test to a separate function. All the test methods and code are
then placed in a class to give a logical grouping.
"""

import logging
import os

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import Qx, TemporaryPreset
from autolib.logconfig import autolib_log
from autolib.testexception import TestException

# We are going to use the main automation library log for this example. In the Qx test suite there is code in the root
# __init__.py that configures logging for the test suite. 
log = logging.getLogger(autolib_log)


@pytest.fixture
def test_qx_hostname():
    """
    A simple fixture that returns a hostname from an environment variable. Generally this fixture would be a global 
    fixture available to all tests to allow for central configuration of a suitable device hostname.
    """
    yield os.getenv("TEST_QX_HOSTNAME", None)


@pytest.fixture(scope='module')
def qx_unit(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname fixture.
    """
    # Create our Qx / QxL object based on the hostname provided by another fixture.
    qx = make_qx(test_qx_hostname)

    module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
    preset_file = f'{module_path}{os.path.sep}_{type(qx).__name__}_basic_test.json'

    # The TemporaryPreset context manager handles upload, activation and eventual deletion of presets to the Qx / QxL
    with TemporaryPreset(qx, preset_file, "basic_test"):

        # The preset will be uploaded to the device and activate. Here before we yield the object we can set additional
        # preconditions on the unit. Let's turn off the bouncing box.
        original_bbox_state = qx.generator.bouncing_box
        qx.generator.bouncing_box = False

        yield qx

        # Fixtures are generator functions so after test has run any teardown can be done here. Let's restore the state
        # of the generator bouncing box prior to the test.
        qx.bouncing_box = original_bbox_state

    # The TemporaryPreset context manager will remove the preset from the Qx / QxL once the test is complete.


@pytest.fixture
def config():
    """
    Pytest fixture that will return a dictionary of configuration settings for tests to use.
    """

    # Here we could get configuration from a database, a static file or (as with the below example) from an
    # environment variable (potentially set by the CI system)

    expected_version = os.getenv("EXPECTED_VERSION", None)
    if not expected_version:
        raise TestException("Please ensure the environment variable EXPECTED_VERSION is set")

    yield {
        'expected_version': expected_version
    }


class TestExampleSuite:
    """
    Tests may be module scope functions of class methods. Classes give a good way of grouping related tests and 
    fixtures can be configured to be created at the start of each test function or once per class (there are additional
    scopes. Please see https://docs.pytest.org/en/stable/fixture.html).

    This test needs to be able to work on Qx / QxL units that are pre and post combined SDI / SDI Stress mode, so
    operation mode is set using request_capability().
    """

    @pytest.mark.sdi
    def test_sdi_operation_mode(self, qx_unit, config):
        """
        Switch the Qx / QxL to SDI mode
        Check the about box reported version number
        Generate 1080p59.94 YCbCr:422:10, 3G_A_Rec.709 with the 100% Bars
        """
        self._sdi_workload(qx_unit, OperationMode.SDI, config['expected_version'])

    @pytest.mark.sdi_stress
    def test_sdi_stress_operation_mode(self, qx_unit, config):
        """
        Place the test device in SDI Stress Toolkit mode and run a set of fundamental tests.
        """
        self._sdi_workload(qx_unit, OperationMode.SDI_STRESS, config['expected_version'])

    def _sdi_workload(self, test_qx, op_mode, expected_version):
        """
        Generalised SDI smoke test parameterised for execution against different standards and test patterns. Note 
        that this is not a test but rather an underscore ('private') method that should only be called from within 
        this class. As a result, we do not list any fixtures in the parameter list.

        :param test_qx: Qx or QxL to perform test on.
        :param op_mode: OperationMode to use for the test (SDI or SDI_STRESS)

        """

        test_pattern = '100% Bars'
        res = '1920x1080p50'
        colour = 'YCbCr:422:10'
        gamut = '3G_A_Rec.709'

        # Set the operating mode and await completion
        log.info(f"Starting test on {test_qx.hostname} - requesting capability {op_mode}")
        test_qx.request_capability(op_mode)

        # Check the reported version number
        assert Qx.RestOperationModeMap[test_qx.about["Software_version"]] == expected_version

        # Check that the four SDI BNC outputs are wired back to the four BNC inputs
        test_qx.io.sdi_input_source = SDIIOType.BNC
        test_qx.io.sdi_output_source = SDIIOType.BNC
        test_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))

        # Start generator
        log.info(f'Setting generator to {res} - {colour} - {gamut} - {test_pattern}')
        test_qx.generator.set_generator(res, colour, gamut, test_pattern)
        assert test_qx.generator.is_generating_standard(res, colour, gamut, test_pattern)

        # Check analyser format matches the generator standard.
        assert test_qx.analyser.get_analyser_status() == (res, colour, gamut)
