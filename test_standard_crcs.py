"""
A test suite that checks that the CRCs for the standards requested are what we
have stored on file.
CRC values will be retrieved from the qx/qxl and then compared with a
golden master record.

The test currently tests per standard, testing each pattern.

The results file is stored in the current directory.
"""

import os
import sys
import time
import pytest
import logging
import pandas as pd
import datetime as date
if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.testexception import TestException
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.generator import GeneratorException
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.qxexception import QxException


# Set up logging
log = logging.getLogger(test_system_log)


# Get ENV Variables
generator = os.getenv('GENERATOR_QX')
analyser = os.getenv('ANALYSER_QX')
test = os.getenv('TEST_QX')


# Initialising global variables
test_passed = True   # Used to store the pass/fail state of the overall test of all standards.
tests_output_results = []    # Used to store the result of the test


# Setting up the test environment
@pytest.fixture(scope='module')
def generator_unit(test_generator_hostname):
    """
    Basic setup for generating standard CRCs:
        * bouncing box set to False
        * output copy set to False
        * set all output source to BNC
        * all SDI outputs set to generator mode
    """
    generator_qx = make_qx(hostname=test_generator_hostname)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.sdi_output_source = SDIIOType.BNC
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'{generator_qx.hostname}: generator setup complete')
    yield generator_qx


@pytest.fixture(scope='module')
def analyser_unit(test_analyser_hostname):
    """
    Basic test set up for analyser:
        * set all SDI output/inputs to BNC
    """
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


@pytest.fixture(scope='module')
def store_test_outcome(env_globals):
    """
    Stores the final results of the test after teardown.
    Note yield being the first line of this method.
    """
    yield
    with open('test_output_file', 'w') as fileName:
        for test_output in test_output_results:
            print(test_output, file=fileName)


# Test function used to load small file containing standards for
# super quick testing.
def load_standard_file(input_file):
    """
    Debugging function, used to quickly test and debug input/output.
    * input_file is a file comprising of a standard on each line, separated by commas, no spaces.
    e.g: 6.0,3840x2160p24,YCbCr:422:10,6G_2-SI_Rec.709
         1.5,1280x720p25,YCbCr:422:10,1.5G_Rec.709
    """
    with open(input_file) as loader:
        input_lines = loader.read().split('\n')

    print(input_lines)
    loaded_stds = []
    for line in input_lines:
        if line == '':
            continue
        loaded_stds.append(line.split(','))

    #data_rate = float(loaded_stds[0][0])
    #resolution = loaded_stds[0][1]
    #mapping = loaded_stds[0][2]
    #gamut = loaded_stds[0][3]

    #if len(loaded_stds[0]) < 4:
    #    raise RuntimeError

    return loaded_stds


@pytest.fixture(scope='module')
def golden_master():
    """
    This reads the golden master file and returns a dataframe.
    """
    today = date.date.today().strftime('%m-%b-%Y')
    today_split = today.split('-')
    day = today_split[0]
    month = today_split[1]
    year = today_split[2]
    # @Arthur crc_dataframe should/can be renamed to reflect the appropriate subset of standards
    # i.e crc_dataframe1.pkl is confidence_test_standards
    #return pd.read_pickle(f'./golden_master-fast-{day}-{month}-{year}.pkl')
    return pd.read_pickle('./crc_dataframe1.pkl')

@pytest.fixture(scope='module')
def env_globals():
    """
    Defines the globals used for storing the test result after teardown.
    """
    yield
    global test_output_results
    global test_passed
    with open('globals-log.txt', 'a') as globalsLogger:
        print(test_passed, file=globalsLogger)


@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.timeout(6000, method='thread')
def test_crcs_all_standards(all_standards, generator_unit, analyser_unit, env_globals, golden_master):
    """
    Wrapper for the test to use the 'all_standards' global fixture.
    """
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _test_crcs_no_assert(generator_unit, analyser_unit, env_globals, all_standards, golden_master)


@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.timeout(600, method='thread')
def test_crcs_confidence(confidence_test_standards, generator_unit, analyser_unit, env_globals, golden_master):
    """
    Wrapper for the test to use the 'confidence_test_standards' global fixture.
    """
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _test_crcs_no_assert(generator_unit, analyser_unit, env_globals, confidence_test_standards, golden_master)


@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.timeout(600, method='thread')
def test_crcs_smoke(smoke_test_standards, generator_unit, analyser_unit, env_globals, golden_master):
    """
    Wrapper for the test to use the 'smoke_test_standards' global fixture.
    """
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _test_crcs_no_assert(generator_unit, analyser_unit, env_globals, smoke_test_standards, golden_master)


@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.timeout(6000, method='thread')
def test_crcs_core(core_test_standards, generator_unit, analyser_unit, env_globals, golden_master):
    """
    Wrapper for the test to use the 'core_test_standards' global fixture.
    """
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _test_crcs_no_assert(generator_unit, analyser_unit, env_globals, core_test_standards, golden_master)


#@pytest.mark.parametrize('standard', load_standard_file('./standards.txt'))   #uncomment for quick testing
def _test_crcs_no_assert(generator_qx, analyser_qx, env_globals, standards_list, golden_master):
    """
    This is an implementation of this test, which uses pytest architecture to test each standard,
    for each test pattern for the crcs are what we expect.
    """
    global test_passed
    standard = standards_list # Done for sake of not changing code all over the place.
    data_rate, resolution, mapping, gamut = standard
    patterns = generator_qx.generator.get_test_patterns(resolution, mapping, gamut)

    # Return a dataframe containing only the 'standard string' in a tuple.
    standard_df = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [(float(data_rate), resolution, mapping, gamut)])]

    # If resulting dataframe is empty, raise an exception.
    if standard_df.empty:
        raise QxException

    # A list to store the indexes of patterns was needed, due to when standard_df is returned, it is returned with
    # the indicies of the original dataframe.
    # So, as a solution, after generating the standard_df, using the .index dataframe method to get all the indexes
    # for all the patterns for a given standard and then store them in a list.
    pattern_index_list = []
    for index in standard_df['Pattern'].index:
        pattern_index_list.append(index)

    # The pattern_index_list can then be iterated using the original pattern_index_gm counter, starting at 0 and incrementing
    # after each pattern.
    pattern_index_gm = 0
    for patt in patterns:
        generator_qx.generator.set_generator(resolution, mapping, gamut, patt)
        qx_settled = generator_qx.generator.is_generating_standard(resolution, mapping, gamut, patt)
        time.sleep(3)
        while qx_settled is False:
            time.sleep(2)
            qx_settled = generator_qx.generator.is_generating_standard(resolution, mapping, gamut, patt)
            time.sleep(2)
            no_crc = analyser_qx.analyser.get_crc_analyser()[0]['activePictureCrc']
            while no_crc == 0:
                no_crc = analyser_qx.analyser.get_crc_analyser()[0]['activePictureCrc']
                time.sleep(2)
        for crc_response in analyser_qx.analyser.get_crc_analyser():
            qx_crc = crc_response['activePictureCrc']
            # assume that the gold master list crc entries are in the same order as they come
            # out of the qx when the test pattern has multiple crcs
            expected_crc = standard_df.loc[pattern_index_list[pattern_index_gm]][2]

            pattern_index_gm += 1
            print(f'Test: {standard} {patt}: Expected CRC: {expected_crc}, Qx_CRC: {qx_crc} ', end='')
            output_entry = [standard, patt, expected_crc, qx_crc]
            if qx_crc == expected_crc[0]:
                output_entry.append('PASS')
                tests_output_results.append(output_entry)
                print('TEST PASSED')
                with open('errResults', 'a') as errWriter:
                    print(f'{standard}, {patt}, {crc_response}', file=errWriter)
                    print(test_passed, file=errWriter)
            else:
                test_passed = False
                output_entry.append('FAIL')
                print('TEST FAILED!!!')
                tests_output_results.append(output_entry)
                with open('errResults', 'a') as errWriter:
                    print(f'{standard}, {patt}, {crc_response}', file=errWriter)
                    print(test_passed, file=errWriter)

    assert test_passed
