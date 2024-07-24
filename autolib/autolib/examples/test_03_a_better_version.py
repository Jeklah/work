"""\
Let's resolve the issues from the previous test one by one.
"""

import logging
import os
import pytest
import time

from autolib.logconfig import autolib_log
from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.generator import GeneratorException
from autolib.testexception import TestException


# The automation library sets up a logger that tests can use. The name of he log is provided in the logconfig module.
log = logging.getLogger(autolib_log)


@pytest.fixture
def qx_unit():
    """
    A PyTest fixture that builds a Qx or QxL (depending on the unit - the factory function determines this for you)
    using the hostname specified by the environment variable TEST_QX_HOSTNAME. There's a lot of repetition potential
    here though to instead, the Qx repo splits this fixture in half - the hostname is determined by a shared fixture
    and the Qx / QxL object is constructed in the fixture in the test module (so that it can have test specific
    set up and tear down).
    """
    qx_hostname = os.getenv("TEST_QX_HOSTNAME")
    if not qx_hostname:
        raise TestException("Please set the environment variable TEST_QX_HOSTNAME to the test device hostname.")
    yield make_qx(qx_hostname)


def standards_list():
    """
    Return a list of 3G and 12G standards where the width is 1920 or 3840 pixels in any YCbCr colour format
    and Rec 709 gamut.
    """
    qx_hostname = os.getenv("TEST_QX_HOSTNAME")
    if not qx_hostname:
        raise TestException("Please set the environment variable TEST_QX_HOSTNAME to the test device hostname.")

    generator_qx = make_qx(qx_hostname)
    return generator_qx.generator.get_matching_standards([3.0, 12.0], r'1920.*|3840.*', r'Y.*', r'.*709'),


# Now our test function has appropriate decorators (the slow marker is for use on tests that take a substantial amount
# of time to run and the sdi_stress marker can be used to run this test along with all SDI Stress tests in a batch with
# the operation mode set at the start of the overall run (usually by the CI server) and uses the qx_unit ficture to
# provide the test with a Qx / Qxl.
#
# In addition to the qx_unit fixture, the PyTest parametrize mark is used. This takes a list of parameter sets and
# generates a test function for each. This is an alternative to the for loop in the previous test example.

@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.parametrize('standard', standards_list())
def test_operation_mode_is_sdi(standard, qx_unit):
    """
    An improved but still non-parameterised test. To parameterise it we will need to generate the standards list in
    a fixture - but we won't have created the fixture when we need the standards list. So in the next version of the
    test we'll solve that.
    """       

    # Capabilities can be requested which will cause implicit configuration to occur. This is currently used to set
    # operation mode without explicitly changing to a specific mode (this was required after 4.3.0 introduced a
    # single combined SDI / SDI Stress mode. It the capability cannot be made available an exception will be thrown
    # to end the test.
    qx_unit.request_capability(OperationMode.SDI_STRESS)

    # You can test the Qx / QxL to see if capabilities are available before continuing
    assert qx_unit.query_capability(OperationMode.SDI_STRESS)

    # Use the logger obtained above instead of print to log test state and use an f-string to embed the hostname and
    # current operation mode (note that these are function calls, not variables. f-string templates can
    # contain expressions.
    log.info(f'{qx_unit.hostname} is in {qx_unit.operation_mode} mode')

    # Now that this test has been parameterised, we no longer need to iterate through a list of standards. As far as
    # the test is concerned it is testing a single standard. We will catch GeneratorExceptions which are raised by
    # the Qx's Generator object when a standard cannot be generated (e.g. if "100% bars" doesn't exist in the
    # standard chosen).
    new_standard = standard[1:]
    try:
        qx_unit.generator.set_generator(*new_standard, "100% Bars")
        for retry in range(10):
            if qx_unit.analyser.get_analyser_status() == new_standard:
                return
            time.sleep(1)
        raise TestException('Failed to lock to the generated standard')
    except GeneratorException as e:
        raise TestException(f'Test case skipped for {standard} - {e}')
