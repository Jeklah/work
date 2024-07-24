"""
This file contains fixtures available to all tests.
"""

import logging
import os
import pytest
import datetime
from pprint import pformat

from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.operationmode import OperationMode

log = logging.getLogger(autolib_log)

# Pull Qx unit IDs from ENV variables
qx_generator = os.getenv("GENERATOR_QX")
qx_analyser = os.getenv("ANALYSER_QX")
qx_testunit = os.getenv("TEST_QX")

if not qx_generator or not qx_analyser or not qx_testunit:
    pytest.exit("Aborting test suite run - env variables GENERATOR_QX, ANALYSER_QX and TEST_QX must all be set.")


@pytest.fixture(scope='session')
def test_qx_hostname():
    """
    The hostname of a single Qx that's being used for all functions of a test.
    """
    return qx_testunit


@pytest.fixture(scope='session')
def test_generator_hostname():
    """
    The hostname of a single Qx that's being used purely as a signal generator or data source.
    """
    return qx_generator


@pytest.fixture(scope='session')
def test_analyser_hostname():
    """
    The hostname of a single Qx that's being used purely as a signal analyser or data analyser.
    """
    return qx_analyser


@pytest.fixture(scope="function", autouse=True)
def test_start_banner(request, test_generator_hostname, test_analyser_hostname):
    """\
    At the start of every test, dump out some information.
    """
    qx_gen = make_qx(test_generator_hostname)
    qx_ana = make_qx(test_analyser_hostname)

    banner = f"""\n
================================ Test Start ===================================
Test name: {request.node.nodeid}
Started: {datetime.datetime.now()}
Test Generator Device: 
  {pformat(qx_gen.about)}

Test Analyser Device: 
  {pformat(qx_ana.about)}      
-------------------------------------------------------------------------------\n"""

    log.info(banner)    # Add to the core test log

    yield

    banner = f"""\n
-------------------------------------------------------------------------------
Test name: {request.node.nodeid}
Ended: {datetime.datetime.now()}
Test Generator Device: 
  {pformat(qx_gen.about)}

Test Analyser Device: 
  {pformat(qx_ana.about)}      
================================= Test End ====================================\n"""

    log.info(banner)    # Add to the core test log


def standard_id_fn(val):
    """
    Make sure the generated test IDs created by metafunc.parametrize below are useful.
    """
    data_rate, res, cmap, gam = val
    return f"{data_rate}-{res}-{cmap}-{gam}"


def pytest_generate_tests(metafunc):
    """
    This is called for every test so always check metafunc.fixturenames and only perform parameterisation of a test
    when requested by the test (e.g. if a test has a fixture 'all_standards' then parameterise the method against
    all supported generator standards.

    Custom options to pytest can handled here but these should be used sparingly (favour environment variables!)
    """

    # The following code will generate a list of testable standards based on the filter criteria and a new test will be
    # created for each instance when a test function uses any of the `all_standards', 'smoke_test_standards' or
    # 'confidence_test_standards' fixtures.

    # There is no need to use `pytest.mark.parameterize` to iterate over different standards, this is taken care of
    # purely by applying one of the aforementioned fixtures to the test method parameters.

    # The fixtures will obtain the standards lists from the Qx / QxL pointed to by the GENERATOR_QX env var

    unit = make_qx(qx_generator)

    # 2110 generation has a different generator
    if not unit.query_capability(OperationMode.IP_2110):

        if 'all_standards' in metafunc.fixturenames:
            # Select all available generation standards (use with care this is a very long list)
            metafunc.parametrize("all_standards",
                                 [[data_rate, res, cmap, gam] for data_rate, res, cmap, gam in unit.generator.standards_generator()],
                                 scope="session",
                                 ids=standard_id_fn)

        elif 'smoke_test_standards' in metafunc.fixturenames:
            # Select standards 3G and 12G standards where the width is 1920 or 3840 pixels in any YCbCr colour format
            # and Rec 709 gamut.
            metafunc.parametrize("smoke_test_standards",
                                 unit.generator.get_matching_standards([3.0, 12.0],
                                                                       r'1920.*|3840.*',
                                                                       r'Y.*',
                                                                       r'.*709'),
                                 scope="session",
                                 ids=standard_id_fn)

        elif 'confidence_test_standards' in metafunc.fixturenames:
            # Select standards for all data rates where they are progressive standards, in YCbCr:422:10 colour format
            # and Rec 709 gamut
            metafunc.parametrize("confidence_test_standards",
                                 unit.generator.get_matching_standards([1.5, 3.0, 6.0, 12.0],
                                                                       r'\d+x\d+p\d+',
                                                                       r'YCbCr:422:10',
                                                                       r'.*709'),
                                 scope="session",
                                 ids=standard_id_fn)
