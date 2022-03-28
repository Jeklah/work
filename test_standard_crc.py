"""
The test that checks the CRCs generated for each test patterns have not changed
in the past 2 releases/versions.

This implementation of the test takes the df for a standard, all its test patterns
and CRCs and compares it with the same df taken from a different version.
This speeds up the test significantly as it does not require the Qx to be generating
live while running the tests.
"""
import json
import logging
import pathlib
import re
import sys

if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')

import pandas as pd
import pytest
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.testexception import TestException


log = logging.getLogger(test_system_log)


@pytest.fixture(scope='module')
def test_qx(test_generator_hostname):
    yield make_qx(hostname=test_generator_hostname)


@pytest.fixture(scope='module')
def current_version(test_qx):
    yield test_qx.about.get('Software_version', None)


@pytest.fixture(scope='module')
def current_data_file(current_version):
    data_path = pathlib.Path(__file__).parent / 'crc_data'
    current_version_file = data_path / f'crcRecord-nightly-{current_version}.json'
    if current_version_file.exists():
        current_data = pd.read_json(current_version_file, orient='table')
        yield current_data
    else:
        raise TestException(f'Could not read JSON data file for current build version {current_version}')


def _get_past_versions():
    """
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


def _read_test_results_json(past_version):
    """
    This reads the last known test results from json files.

    Parameters:
        * generator_qx object
        * past_vers string
    """

    data_path = pathlib.Path(__file__).parent / 'crc_data'
    past_version_file = data_path / f'crcRecord-nightly-{past_version}.json'
    if past_version_file.exists():
        with open(past_version_file) as past_version_json:
            metadata = json.load(past_version_json).get('metadata')
            log.info(f'Loaded stored crc dataframe with metadata: {metadata}')
        return pd.read_json(past_version_file, orient='table')
    else:
        raise TestException(f'Could not read JSON data file for version {past_version}')


@pytest.mark.sdi
@pytest.mark.parametrize('past_vers', _get_past_versions())
def test_crcs(test_qx, current_data_file, past_vers):
    """
    Compares CRCs of all test_patterns for a standard to previous versions.

    Parameters:
        * generator_qx object
        *
        *
    """
    past_data_file = _read_test_results_json(past_vers)
    assert current_data_file.equals(past_data_file)
