"""
A suite of tests to check the generated standards match the CRCs we have stored on file.
"""
import pdb
import logging
import time
import pytest
import pandas as pd
from test_system.retry import retry, retry_ignoring_exceptions
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode

log = logging.getLogger(test_system_log)


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates generator qx object using test_generator_hostname global. All tests in this
    suite are SDI tests and require the bouncing box and output copy to be disabled.
    """
    gen_qx = make_qx(hostname=test_generator_hostname)
    gen_qx.request_capability(OperationMode.SDI)
    gen_qx.generator.bouncing_box = False
    gen_qx.generator.output_copy = False
    gen_qx.generator.jitter_insertion("Disabled", 0.01, 10)
    gen_qx.io.sdi_output_source = SDIIOType.BNC
    gen_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f"FIXTURE: Qx {gen_qx.hostname} setup complete.")
    yield gen_qx
    gen_qx.generator.bouncing_box = False
    log.info(f"FIXTURE: Qx {gen_qx.hostname} teardown complete.")


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
    golden_master = pd.read_pickle('./crc_dataframe1.pkl')
    return golden_master


def gen_std_list(gen_qx, stds='fast'): # Adding this method to generate list of standards from the unit
    if stds == 'nightly': # Nightly filter, requirements agreed upon in the meeting.
        standards_list = gen_qx.generator.get_matching_standards(
            [1.5],
            r"720.*|1920.*|2048.*|3840.*|4096.*",
            r"RGB.*|YCbCr:422:10|YCbCr:422:12|YCbCr:444:.*",
            r".*709|.*2020|HLG.*|PQ.*}S-Log3.*",
        )
    elif stds == 'test':
        standards_list = gen_qx.generator.get_matching_standards(
            [1.5],
            r"1920.*",
            r"YCbCr:422:10",
            r".*709"
        )
    elif stds == 'fast': # This filter was added to speed up development. It returns 5 standards.
        standards_list = gen_qx.generator.get_matching_standards(
            [1.5, 3.0],
            r"(1920x1080|1280x720)[i|p]50",
            r"YCbCr:422:10",
            r".Rec.709"
        )
    elif stds == 'confidence_test_standards': # This is the same filter as found in conftest.py
        standards_list = gen_qx.generator.get_matching_standards(
            [1.5, 3.0, 6.0, 12.0],
            r"\d+x\d+p\d+",
            r"YCbCr:422:10",
            r".*709"
        )
    elif stds == 'all':
        all_stds = gen_qx.generator.get_standards()
        standards_list = [
            [data_rate, resolution, colour_map, gamut]
            for data_rate in all_stds
            for resolution in all_stds[data_rate]
            for colour_map in all_stds[data_rate][resolution]
            for gamut in all_stds[data_rate][resolution][colour_map]
        ]
    else:
        print('stds filter was not set')
    return standards_list


#@pytest.fixture(scope='module')
def get_std_and_pattern_params(gen_qx, standards_list):
    """
    Retrive the standard parameters from unit being tested to parametrize tests with.
    """
    crcs = []
    for row in standards_list:
        data_rate, res, mapping, gamut = row  #golden_master.get('Standard')[row][0]
        test_patterns = gen_qx.generator.get_test_pattern(row[0], row[1], row[2])
        for pattern in test_patterns:
            crc_resp = gen_qx.analyser.get_crc_analyser() # this needs to be retrieved from golden master!
            crcs = [x.get('activePictureCrc', None) for x in crc_resp] # this is derived from the line above
            yield data_rate, res, mapping, gamut, pattern, crcs   #here


@pytest.mark.parametrize("data_rate, res, mapping, gamut, pattern", get_std_and_pattern_params(generator_qx, gen_std_list(generator_qx, stds='fast')))
def test_generate_test_pattern(generator_qx, analyser_qx, data_rate, res, mapping, gamut, pattern):
    """
    Generate a given test_pattern for a given standard and checks it is generating
    what is requested.
    """
    gen_qx.generator.set_generator(res, mapping, gamut, pattern)
    assert gen_qx.generator.generator_status.get('pattern', None) == pattern


@pytest.mark.parametrize("data_rate, res, mapping, gamut, pattern, crcs", get_std_and_pattern_params(generator_qx, gen_std_list(generator_qx, stds='fast')))
def test_pattern_crc(generator_qx, analyser_qx, data_rate, res, mapping, gamut, pattern, crcs):
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
    gen_qx.generator.set_generator(res, mapping, gamut, pattern)

    gen_success, _, genErr = retry(10, 1, gen_qx.generator.is_generating_standard, res, mapping, gamut, pattern)
    if not gen_success:
        pytest.fail(f"Generator didn't report generation of the standard and pattern requested. {genErr}")

    analys_success, _, analysErr = retry_ignoring_exceptions(10, 1, analyser_qx.analyser.expected_video_analyser, res, mapping, gamut)
    if not analys_success:
        pytest.fail(f"Analyser didn't report analysis of the standard and pattern requested. {analysErr}")

    assert gen_qx.generator.generator_status.get('pattern', None) == pattern

    # Check CRCs
    crc_response = []
    for _ in range(10):
        crc_response = gen_qx.analyser.get_crc_analyser()
        if crc_response[0].get('activePictureCrc', None) != "0":
            break
        time.sleep(1)
    else:
        pytest.fail('Failed to read active picture CRCs')

    # Check the number of crcs are the same as expected
    pict_crcs = [crc.get('activePictureCrc', None) for crc in crc_response]
    assert len(crcs) == len(pict_crcs)

    # Check the values of the CRCs are the same as expected
    for expected_crc, recorded_crc in zip(crcs, pict_crcs):
        assert expected_crc == recorded_crc


