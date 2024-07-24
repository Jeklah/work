"""
A small suite of  tests that will request generation of the same standard twice in a row to make sure
the ReST API and GUI behave in the desired manner in this situation.
"""

import os
import pytest
import logging

from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode
from autolib.logconfig import autolib_log

log = logging.getLogger(autolib_log)
test_generator_hostname = os.getenv('GENERATOR_QX')


@pytest.fixture(scope='module')
def config():
    return {
        "resolution": "1920x1080p50",
        "colour": "YCbCr:422:10",
        "gamut": "3G_B_Rec.709",
        "test_pattern": "100% Bars"
    }


@pytest.fixture
def generator_qx(test_generator_hostname):
    """
    Create a Qx object configured for the test run to act as a generator.

    PyTest fixtures will create a Qx object using the test_generator_hostname global variable and setup
    the unit before the test is run and then perform teardown operations afterward.
    """
    generator_qx = make_qx(test_generator_hostname)
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    log.info(f'FIXTURE: Generator Qx {generator_qx.hostname} setup complete.')
    yield generator_qx
    log.info(f'FIXTURE: Generator Qx {generator_qx.hostname} teardown complete.')


def test_generate_same_standard(generator_qx, config):
    """
    Test to generate the same standard 5 times in a row.
    """
    for attempt in range(5):
        generator_qx.generator.set_generator(config['resolution'], config['colour'], config['gamut'], config['test_pattern'])
        assert generator_qx.generator.is_generating_standard(config['resolution'], config['colour'], config['gamut'], config['test_pattern']), f'Attempt {attempt} to set standard failed.'
