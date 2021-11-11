"""
A test suite that checks the CRCs for the standards requested are what we
have stored on file.
CRC values will be retrieved from the qx/qxl and then compared with a
golden master record.

Any failures mean an investigation is needed.
The test currently tests per standard, testing each pattern with boolean flags.
"""

import os
import sys
import time
import pytest
import logging
import pandas as pd
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


# Initialising global variables (these might be able to be passed around as local)
TEST_PASSED = True
TESTS_OUTPUT = []


# Setting up the test environment
@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
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
def analyser_qx(test_analyser_hostname):
    """
    Basic test set up for analyser:
        * set all SDI output/inputs to BNC
    """
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


# Test function used to load small file containing standards for
# super quick testing.
def load_file(input_file):
    """
    Debugging function, used to quickly test and debug input/output.
    """
    with open(input_file) as loader:
        input_lines = loader.read().split('\n')

    loaded_stds = []
    for line in input_lines:
        if line == '':
            continue
        loaded_stds.append(line.split(','))

    data_rate = float(loaded_stds[0][0])
    resolution = loaded_stds[0][1]
    mapping = loaded_stds[0][2]
    gamut = loaded_stds[0][3]

    return loaded_stds


@pytest.fixture
def golden_master():
    """
    This loads the golden_master file.
    @Arthur crc_dataframes should/can be renamed to reflect the appropriate subset of standards.
    """
    return pd.read_pickle('./crc_dataframe1.pkl')


#@pytest.mark.parametrize('standard', load_file('./standards.txt'))   #uncomment for quick testing
#def test_crcs_no_assert(generator_qx, analyser_qx, standard, golden_master):
def test_crcs_no_assert(generator_qx, analyser_qx, confidence_test_standards, golden_master):
    """
    This is an implementation of this test, which uses pytest architecture to test per standard,
    then boolean flags are used to test each test pattern for a given standard.
    """
    # standard = confidence_test_standards                                                        # Done for sake of not changing code all over the place.
    # data_rate, resolution, mapping, gamut = standard[0], standard[1], standard[2], standard[3]  # Similarly, as well as giving them proper names and readability.
    data_rate, resolution, mapping, gamut = confidence_test_standards[0], confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3]
    patterns = generator_qx.generator.get_test_patterns(resolution, mapping, gamut)

    # change structure of golden master so that data_rate is a float.
    # Return a dataframe containing only the 'standard string' in a tuple.
    #standard_df = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [(float(data_rate), resolution, mapping, gamut)])]

    # Less complex way of achieving the above..
    #df_search_for_std = [(float(data_rate), str(resolution), str(mapping), str(gamut))]
    #print(f'df :{df_search_for_std}. type: {type(df_search_for_std)}')
    standard_df = golden_master.loc[golden_master['Pattern'].isin([confidence_test_standards])]

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
    # after each pattern. Enumerate may be a better choice here (instead of manually incremeting an index), since we need both values and indexes.
    pattern_index_gm = 0
    for patt in patterns:
        generator_qx.generator.set_generator(confidence_test_standards)
        time.sleep(2)
        qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards)
        while qx_settled is False:
            qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards)
            # a possible time.sleep(2) is needed here to stop the 0 crcs from qx?
            time.sleep(2)

        for crc_response in analyser_qx.analyser.get_crc_analyser():
            qx_crc = crc_response['activePictureCrc']
            # assume that the gold master list crc entries are in the same order as they come
            # out of the qx when the test pattern has multiple crcs
            expected_crc = standard_df.loc[pattern_index_list[pattern_index_gm]][2]

            pattern_index_gm += 1
            print(f'Test: {confidence_test_standards} {patt}: Expected CRC: {expected_crc}, Qx_CRC: {qx_crc} ', end='')
            output_entry = [confidence_test_standards, patt, expected_crc, qx_crc]
            if qx_crc == expected_crc[0]:
                output_entry.append('PASS')
                print('TEST PASSED')
            else:
                TEST_PASSED = False
                output_entry.append('FAIL')
                print('TEST FAILED!!!')

            TESTS_OUTPUT.append(output_entry)


def test_results():
    """
    Write results to results file.
    """
    with open('results', 'w') as f:
        for entry in TESTS_OUTPUT:
            print(entry, file=f)

    assert TEST_PASSED is True

