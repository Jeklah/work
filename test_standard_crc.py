"""
The test that checks the CRCs generated for each test patterns have not changed
in the past 2 releases/versions.

This implementation of the test takes the df for a standard, all its test patterns
and CRCs and compares it with the same df taken from a different version.
This speeds up the test significantly as it does not require the Qx to be generating
live while running the tests.
"""
import logging
import os.path
import pandas as pd
import pathlib
import pytest
import re
import sys

if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')

from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.testexception import TestException
from test_system.models.qxseries.io import SDIIOType


# Set up logging
log = logging.getLogger(test_system_log)


# Setting up the test environment
@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Basic setup for generating standard CRCs:
        * Bouncing box set to False
        * Output copy set to False
        * Set all output source to BNC
        * All SDI outputs set to generator mode

    Parameters:
        * test_generator_hostname string
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

    Parameters:
        * test_analyser_hostname string
    """
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


# Test function used for super quick testing.
def load_standard_file(input_file):
    """
    Debugging function.
        * input_file is a file compromising of a standard on each line, seperated by commas, no spaces.
    e.g: 6.0,3840x2160p24,YCbCr:422:10,6G_2-SI_Rec.709
         1.5,1280x720p25,YCbCr:422:10,1.5G_Rec.709

    Parameters:
        * input_file string
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
    """\
    Get a list of the versions for which JSON files exist in the crc_data folder that match:

        crcRecord-nightly-<x.y.x>.json

    """
    mod_path = pathlib.Path(__file__).parent / 'crc_data'
    versions = []
    for jsonfile in mod_path.glob('*.json'):
        if jsonfile.is_file():
            match = re.search(r'crcRecord-nightly-(?P<fw_ver>\d{1,4}\.\d{1,4}\.\d{1,4}).json', jsonfile.name)
            if match:
                versions.append(match.group('fw_ver'))
    return list(versions)


def read_last_test_results_pickle(generator_qx, past_vers=get_past_versions()):
    """
    This reads the last known test results from pickle files.
    Keeping this function as the test actually performs better when
    comparing pkl files rather than json files.

    Parameters:
        * generator_qx object
        * past_vers string
    """
    curr_vers = generator_qx.about['Software_version']
    try:
        if os.path.exists(f'./crcRecord-nightly-{past_vers}.pkl'):
            return pd.read_pickle(f'./CRC_Checks/crcRecord-nightly-{curr_vers}.pkl'), curr_vers, \
                   pd.read_pickle(f'./CRC_Checks/crcRecord-nightly-{past_vers}.pkl')
        else:
            return pd.read_pickle(f'./CRC_Checks/crcRecord-nightly-{curr_vers}.pkl'), \
                   pd.read_pickle('./CRC_Checks/crc_corr_check.pkl')
    except FileNotFoundError as ferr:
        log.error(f'The file for a previous version could not be found. {ferr}')


def read_last_test_results_json(generator_qx, past_vers=get_past_versions()):
    """
    This reads the last known test results from json files.

    Parameters:
        * generator_qx object
        * past_vers string
    """
    curr_vers = generator_qx.about['Software_version']
    try:
        if os.path.exists(f'./CRC_Checks/crcRecord-nightly-{past_vers}.json'):
            return pd.read_json(f'./CRC_Checks/crcRecord-nightly-{curr_vers}.json', orient='table'), curr_vers, \
                   pd.read_json(f'./CRC_Checks/crcRecord-nightly-{past_vers}.json', orient='table')
    except FileNotFoundError as ferr:
        log.error(f'The file for the previous version could not be found. {ferr}')


@pytest.mark.sdi
@pytest.mark.parametrize('past_vers', get_past_versions())
def test_crcs(generator_qx, confidence_test_standards, past_vers):
    """
    Compares CRCs of all test_patterns for a standard to previous versions.

    Parameters:
        * generator_qx object
        * confidence_test_standards tuple
        * past_vers string
    """
    std = confidence_test_standards
    todays_results, curr_vers, recent_results = read_last_test_results_json(generator_qx, past_vers)
    #todays_results, curr_vers, recent_results = read_last_test_results_pickle(generator_qx, past_vers)
    standard_df = todays_results.loc[todays_results['Standard'] == std]

    try:
        pattern_index_list = []
        for index in standard_df['Pattern'].index:
            pattern_index_list.append(index)

    except TestException as terr:
                log.error(f'The standard could not be found: {terr}')
    test_patterns = standard_df['Pattern'].values.tolist()

    # get crcs for the standard being tested.
    # they will be in the same order as the test pattern list, so they can use the same index.
    crc_list = standard_df['CrcValue'].values.tolist()

    print(f'Checking standard: {std}, versions: {curr_vers} against {past_vers} ')
    for patt, crc in zip(test_patterns, crc_list):
        assert recent_results[(recent_results['Standard'] == std)].equals(todays_results[(todays_results['Standard'] == std)])
        tmp_df = recent_results[['Standard', 'Pattern', 'CrcValue']]
        test_pattern_crc_df = tmp_df[tmp_df['Standard'] == std]

        todays_tmp_df = todays_results[['Standard', 'Pattern', 'CrcValue']]
        todays_test_pattern_crc_df = todays_tmp_df[todays_tmp_df['Standard'] == std]

        assert todays_test_pattern_crc_df.equals(test_pattern_crc_df)
