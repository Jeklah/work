"""
The test that checks the CRCs generated for each test patterns have not changed
in the past 2 releases/versions.

The results file is stored in the current directory.
"""
import sys
import pytest
import logging
import os.path
import pandas as pd
if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.testexception import TestException
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.qxexception import QxException
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.generator import GeneratorException


# Set up logging
log = logging.getLogger(test_system_log)


# Get ENV variables
generator = os.getenv('GENERATOR_QX')
analyser = os.getenv('ANALYSER_QX')
test = os.getenv('TEST_QX')


# Initialising global variables
test_passed = True        # Used to store the pass/fail state of the overall test of all standards (?)
tests_output_results = [] # Used to store the result of the test


# Setting up the test environment
@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Basic setup for generating standard CRCs:
        * Bouncing box set to False
        * Output copy set to False
        * Set all output source to BNC
        * All SDI outputs set to generator mode
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
        * Set all SDI output/inputs to BNC
    """
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


# Also questionable. From all that I've read, globals are a bad idea, especially when testing.
# Would like to remove these, if not already redundant.
@pytest.fixture(scope='module')
def env_globals():
    """
    Defines any needed globals used for storing the test result after teardown.
    """
    yield
    global test_output_results
    global test_passed
    with open('globals-log.txt', 'a') as globalLogger:
        print(test_passed, file=globalLogger)


# Questionable. Is this needed for this implementation of the test?
@pytest.fixture(scope='module')
def store_test_outcome(env_globals):
    """
    Stores the final results of the test after teardown.
    Note: yield being used in first line ensures this is run at the end of a test.
    """
    yield
    with open('test_results', 'w') as fileName:
        for test_output in test_output_results:  # global
            print(test_output, file=fileName)


# Test function used for super quick testing.
def load_standard_file(input_file):
    """
    Debugging function.
        * input_file is a file compromising of a standard on each line, seperated by commas, no spaces.
    e.g: 6.0,3840x2160p24,YCbCr:422:10,6G_2-SI_Rec.709
         1.5,1280x720p25,YCbCr:422:10,1.5G_Rec.709
    """
    with open(input_file) as loader:
        input_lines = loader.read().split('\n')

    loaded_stds = []
    for line in input_lines:
        if line == '':
            continue
        loaded_stds.append(line.split(','))

    return loaded_stds


def get_past_versions():
    """
    Yield past versions to test against.
    """
    versions = [
               "4.3.1",
               "4.4.0",
               "4.5.0",
               ]
    for vers in versions:
        yield vers


@pytest.mark.parametrize('past_vers', get_past_versions())
def read_last_test_results(generator_qx, past_vers):
    """
    This reads the last known test results.
    """
    # today = date.date.fromordinal(date.date.today().toordinal() -1).strftime('%m-%b-%Y')
    # today_split = today.split('-')
    # day = today_split[0]
    # month = today_split[1]
    # year = today_split[2]
    # yesterday = int(day) - 1
    curr_vers = generator_qx.about['Software_version']
    try:
        if os.path.exists(f'./crcRecord-nightly-{past_vers}.pkl'):
            return pd.read_pickle(f'./crcRecord-nightly-{curr_vers}.pkl'), curr_vers, \
                   pd.read_pickle(f'./crcRecord-nightly-{past_vers}.pkl')
        else:
            return pd.read_pickle(f'./crcRecord-nightly-{curr_vers}.pkl'), \
                   pd.read_pickle('./crc_corr_check.pkl')
    except FileNotFoundError as ferr:
        log.error(f'The file for a previous version could not be found. {ferr}')


@pytest.mark.parametrize('past_vers', get_past_versions())
def test_crcs(generator_qx, confidence_test_standards, past_vers):
    std = confidence_test_standards
    todays_results, curr_vers, recent_results = read_last_test_results(generator_qx, past_vers)
    standard_df = todays_results.loc[todays_results['Standard'] == std]

    if len(standard_df) == 0:
        pytest.xfail
    # get index for patterns for the standard.
    pattern_index_list = []
    for index in standard_df['Pattern'].index:
        pattern_index_list.append(index)

    # get test_patterns for the standard being tested.
    test_patterns = standard_df['Pattern'].values.tolist()

    # get crcs for the standard being tested.
    # they will be in the same order as the test pattern list, so they could use the same index.
    crc_list = standard_df['CrcValue'].values.tolist()

    print(f'Checking standard: {std}, versions: {curr_vers} against {past_vers} ')
    pattern_index = 0
    for patt, crc in zip(test_patterns, crc_list):
        assert recent_results[(recent_results['Standard'] == std)].equals(todays_results[(todays_results['Standard'] == std)])
        # breakpoint()
        tmp_df = recent_results[['Standard', 'Pattern', 'CrcValue']]
        test_pattern_crc_df = tmp_df[tmp_df['Standard'] == std]


        todays_tmp_df = todays_results[['Standard', 'Pattern', 'CrcValue']]
        todays_test_pattern_crc_df = todays_tmp_df[todays_tmp_df['Standard'] == std]

        assert todays_test_pattern_crc_df.equals(test_pattern_crc_df)


