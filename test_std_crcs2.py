"""
A suite of tests to check the generated standards match the CRCs we have stored on file.
"""

import logging
import os
import time
import pytest
import pandas as pd
from test_system.retry import retry, retry_ignoring_exceptions
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.qx import TemporaryPreset
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode

log = logging.getLogger(test_system_log)


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates generator qx object using test_generator_hostname global. All tests in this
    suite are SDI tests and require the bouncing box and output copy to be disabled.
    """
    generator_qx = make_qx(hostname=test_generator_hostname)
    generator_qx.request_capability(OperationMode.SDI)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.generator.jitter_insertion("Disabled", 0.01, 10)
    generator_qx.io.sdi_output_source = SDIIOType.BNC
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f"FIXTURE: Qx {generator_qx.hostname} setup complete.")
    yield generator_qx
    generator_qx.generator.bouncing_box = False
    log.info(f"FIXTURE: Qx {generator_qx.hostname} teardown complete.")


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    """
    Creates analyser qx object using test_analyser_hostname global.
    """
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.request_capability(OperationMode.SDI)
    analyser_qx.io.sdi_input_source = SDIIOType.BNC
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} setup complete.")
    yield analyser_qx
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} teardown complete.")


def load_goldenmaster():
    """
    Loads the golden master file from file into the program.
    """
    golden_master = pd.read_pickle('./crc_dataframe.pkl')
    return golden_master


# @pytest.fixture(scope='module')
def get_std_and_pattern_params(golden_master):
    """
    Retrive the standard parameters from golden_master to parametrize tests with.
    """
    crcs = []
    for row in golden_master:
        data_rate, res, mapping, gamut = golden_master.get('Standard')[row][0]
        test_pattern = golden_master.get('Pattern')[row]
        crc_count = golden_master.get('CrcCount')[row]
        crc_resp = generator_qx.analyser.get_crc_analyser()
        crcs = [x.get('activePictureCrc', None) for x in crc_resp]
        yield data_rate, res, mapping, gamut, test_pattern, crcs


@pytest.mark.parametrize("data_rate", "res", "mapping", "gamut", get_std_and_pattern_params(load_goldenmaster()))
def test_generate_test_pattern(generator_qx, analyser_qx, data_rate, res, mapping, gamut, test_pattern):
    """
    Generate a given test_pattern for a given standard and checks it is generating
    what is requested.
    """
    generator_qx.generator.set_generator(res, mapping, gamut, test_pattern)
    assert generator_qx.generator.generator_status.get('pattern', None) == test_pattern


@pytest.mark.parametrize("data_rate", "res", "mapping", "gamut", "test_pattern", "crcs", get_std_and_pattern_params(load_goldenmaster()))
def test_pattern_crc(generator_qx, analyser_qx, data_rate, res, mapping, gamut, test_pattern, crcs):
    """
    Checks that the generated test_pattern/s has the expected crc/s

    * Disable the bouncing box
    * Generate a standard given standard
    * Allow 5s for the analyser to settle
    * Confirm that the generator thinks it's generating the right standard and test_pattern
    * Confirm that the analyser thinks it's receiving the correct standard
    * Check the test pattern in the generator status is the requested pattern
    * Get the active frame CRCs from the analyser and compare to expected CRCs found in golden master
    """
    generator_qx.generator.set_generator(res, mapping, gamut, test_pattern)

    gen_success, _, genErr = retry(10, 1, generator_qx.generator.is_generating_standard, res, mapping, gamut, test_pattern)
    if not gen_success:
        pytest.fail(f"Generator didn't report generation of the standard and pattern requested. {genErr}")

    analys_success, _, analysErr = retry_ignoring_exceptions(10, 1, analyser_qx.analyser.expected_video_analyser, res, mapping, gamut)
    if not analys_success:
        pytest.fail(f"Analyser didn't report analysis of the standard and pattern requested. {analysErr}")

    assert generator_qx.generator.generator_status.get('pattern', None) == test_pattern

    # Check CRCs
    crc_response = []
    for _ in range(10):
        crc_response = generator_qx.analyser.get_crc_analyser()
        if crc_response[0].get('activePictureCrc', None) != "0":
            break
        time.sleep(1)
    else:
        pytest.fail('Failed to read active picture CRCs')

    # Check the number of crcs are the same as expected
    pict_crcs = [crc.get('activePictureCrc', None) for crc in crc_response]
    assert crc_count == len(pict_crcs) # REMOVE: use of crc_count not needed

    # Check the values of the CRCs are the same as expected
    for expected










