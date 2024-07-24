"""\
This is a more realistic test that demonstrates mode features of the Phabrix automation library.

There are three fixtures in this test:

  * test_qx_hostname - this returns the content of an environment variable TEST_QX_HOSTNAME or informs the user if
                       this is not set. This is run at module scope.

  * qx_unit - This fixture creates an appropriate Qx series object for the test to use. It performs module-level setup
              and teardown of the device, configures it for the test and restores the pre-test state at completion.

  * config - This fixture passes a dictionary of configuration settings into the tests. In this case the fixture obtains
             and returns a single environment variable value (EXPECTED_VERSION).

Importantly, this test demonstrates how a test can be written such that there are subtly different versions for
different operating modes by moving the body of the test to a separate function. The two tests are thin wrappers around
a common function with differing parameters used for each execution. All the test methods and code are then placed in a
class to give a logical grouping.

There is a generalised mechanism for parameterising tests like this using the @pytest.mark.parametrize decorator which
we briefly saw in example 3 and will be covered in future examples.
"""

import logging
import os

import pytest

from autolib.retry import retry_ignoring_exceptions
from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import StateSnapshot
from autolib.models.qxseries.analyser import FrameType
from autolib.logconfig import autolib_log
from autolib.testexception import TestException

# We are going to use the main automation library log for this example. In the Qx test suite there is code in the root
# __init__.py that configures logging for the test suite. 
log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def test_qx_hostname():
    """
    A simple fixture that returns a hostname from an environment variable. Generally this fixture would be a global 
    fixture available to all tests to allow for central configuration of a suitable device hostname.
    """
    hostname = os.getenv("TEST_QX_HOSTNAME", None)
    if hostname:
        yield hostname
    else:
        raise TestException("Please set the environment variable TEST_QX_HOSTNAME to the host name of the test device.")


@pytest.fixture(scope='module')
def qx_unit(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname fixture.
    """
    # Create our Qx / QxL object based on the hostname provided by another fixture.
    qx = make_qx(test_qx_hostname)

    # The StateSnapshot context manager stores the state as a preset which is then optionally
    # set when the with block completes. This is useful for restoring the state after a test completes.
    with StateSnapshot(qx, restore=True) as start_state:

        # We've stored the state so let's configure the unit for the test. Let's turn off the bouncing box.
        qx.generator.bouncing_box = False

        yield qx

        # Fixtures are generator functions so after test has run any teardown can be done here. As we've used
        # the StateSnapshot though, the initial state of the unit will be automatically restored when this 
        # block of code completes.


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
        assert test_qx.about["Software_version"] == expected_version

        # Check that the four SDI BNC outputs are wired back to the four BNC inputs
        test_qx.io.sdi_input_source = SDIIOType.BNC
        test_qx.io.sdi_output_source = SDIIOType.BNC
        test_qx.io.set_sdi_output_source(SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4)

        # Start generator
        log.info(f'Setting generator to {res} - {colour} - {gamut} - {test_pattern}')
        test_qx.generator.set_generator(res, colour, gamut, test_pattern)
        assert test_qx.generator.is_generating_standard(res, colour, gamut, test_pattern)

        # Check analyser format matches the generator standard.
        # As the analyser can take a moment to lock, instead of a time.sleep() which is very
        # bad practice, we'll use the retry method from autolib to try and get the standard five times until
        # we either receive a ParsedStandard object else fail the test.
        success, parsed_standard, exc = retry_ignoring_exceptions(5, 2, test_qx.analyser.sdi.get_parsed_standard)
        assert success

        # Check to see if the state we care about is as expected.
        assert parsed_standard.data_rate == 3.0 and parsed_standard.resolution.width == 1920 and parsed_standard.resolution.height == 1080
        assert parsed_standard.frame_type == FrameType.PROGRESSIVE
