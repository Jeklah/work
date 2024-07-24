"""\
The test that checks the CRCs generated for each test patterns have not changed
in the past 2 releases/versions.

This implementation of the test takes the df for a standard, all its test patterns
and CRCs and compares it with the same df taken from a different version.
This speeds up the test significantly as it does not require the Qx to be generating
live while running the tests.
"""

import json
import logging
import os
import pathlib
import re
import sys

if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')

import pandas as pd
import pytest
import pkg_resources
from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.testexception import TestException
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.input_output import SDIIOType
import verify_std_with_patterns as verify

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def test_qx(test_generator_hostname) -> object:
    """
    Yields a qx object for testing.

    :return: qx object
    """
    test_qx = make_qx(test_generator_hostname)
    test_qx.request_capability(OperationMode.SDI)
    test_qx.io.sdi_output_source = SDIIOType.BNC
    yield test_qx


@pytest.fixture(scope='module')
def test_analyser_qx(test_analyser_hostname) -> object:
    """
    Yields a qx object for testing.

    :param test_analyser_hostname: str
    :return: qx object
    """
    test_analyser_qx = make_qx(test_analyser_hostname)
    test_analyser_qx.request_capability(OperationMode.SDI)
    test_analyser_qx.io.sdi_input_source = SDIIOType.BNC
    yield test_analyser_qx


@pytest.fixture(scope='module')
def current_version(test_qx) -> str:
    """
    Yields the current software version installed on the test_qx of the form "x.y.z-build".

    :param test_qx: qx object
    :return: str
    """
    yield f"{test_qx.about.get('Software_version', None)}-{test_qx.about.get('Build_number', None)}"


@pytest.fixture(scope='module')
def current_data(current_version):
    """
    Yields the dataset for the current installed version on the test Qx.

    :param current_version: str
    """
    data_path = pathlib.Path(__file__).parent / 'crc_data'
    current_version_file = data_path / f'crcRecord-nightly-{current_version}.json'
    if current_version_file.exists():
        yield pd.read_json(current_version_file, orient='table')
    else:
        raise TestException(
            f'Could not read JSON data file for current build version {current_version}.'
        )


@pytest.fixture(scope='module')
def nightly_data(test_qx, test_analyser_qx):
    """
    Generate a nightly set of CRC values in crc_data and yield the JSON filename. The file is placed in the test's
    crc_data folder where the test will pick it up and use it as the basis of comparison (as it'll have a more recent
    version number than any present files).
    """
    module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
    version = f'{test_qx.about["Software_version"]}-{test_qx.about["Build_number"]}'
    file_path = f'{module_path}/crc_data/crcRecord-{verify.StandardsSubset.NIGHTLY.value}-{version}.json'
    nightly_crc_file = verify.generate_crc_record_file(test_qx, test_analyser_qx, verify.gen_std_list(test_qx, verify.StandardsSubset.NIGHTLY), file_path)
    yield nightly_crc_file, version


def _latest_version():
    """
    Returns the latest version of data stored in crc_data
    :return: string of latest version.
    """
    versions = [str(pkg_resources.parse_version(ver)).replace('.post', '-') for ver in _get_past_versions()]

    return sorted(versions, reverse=True)[0]


def _get_past_versions() -> list:
    """
    Get a list of the versions for which JSON files exist in the crc_data folder that match:

        crcRecord-nightly-<x.y.z-build>.json

    :return: List of version strings
    """
    return _get_versions(pathlib.Path(__file__).parent / 'crc_data')


def _get_versions(mod_path) -> list:
    """
    Get a list of the versions for which JSON files exist in the crc_data folder that match:

        crcRecord-nightly-<x.y.z>.json

    :return: List of version strings
    """
    versions = []
    for jsonfile in mod_path.glob('*.json'):
        if jsonfile.is_file():
            match = re.search(r'crcRecord-nightly-(?P<fw_ver>\d{1,4}\.\d{1,4}\.\d{1,4}-\d{1,8}).json', jsonfile.name)
            if match:
                versions.append(match.group('fw_ver'))
    return list(versions)


def _get_sad_test_versions() -> list:
    """
    Get a list of the versions for which JSON files exist in the sad_test_crc_data folder that match:

        crcRecord-nightly-<x.y.z-build>.json

    These files are crafted to ensure that the test is correctly failing on data that is broken in various ways.

    :return: versions list
    """
    return _get_versions(pathlib.Path(__file__).parent / 'sad_test_crc_data')


def _read_results_json(past_version: str) -> pd.DataFrame:
    """
    This reads the last known test results from JSON files.

    :param past_version: Version number used to identify the file to load
    :return: DataFrame containing the requested data
    """
    data_path = pathlib.Path(__file__).parent / 'crc_data'
    past_version_file = data_path / f'crcRecord-nightly-{past_version}.json'
    if past_version_file.exists():
        with open(past_version_file) as past_version_json:
            metadata = json.load(past_version_json).get('metadata')
            log.info(f'Loaded store crc dataframe with metadata: {metadata}')
        return pd.read_json(past_version_file, orient='table')
    else:
        raise TestException(f'Could not read JSON data file for version {past_version}')


def _check_data_size_valid(latest_version: str, past_version: str) -> tuple:
    """
    Compares the dataset size/shape of current installed version to past versions.

   .. note::
      Shape does not need to be checked due to .equals handling as long as the columns are the same, which they will
      be as the JSON column names are defined within the tests. What DOES need to be checked is whether the current
      version has less data than the past version (FAIL) as well as if the current version has more data (PASS but must
      log discrepancy).

    :param latest_version: Version number of the latest software
    :param past_version: Version number as a string of an arbitrary versions
    :return: bool
    """
    latest_data = _read_results_json(latest_version)
    past_data = _read_results_json(past_version)
    if len(latest_data) > len(past_data):
        log.warning(
            f'Comparison of current and past CRC data files shows that {latest_data} has more data than {past_data}'
            )
    elif len(past_data) > len(latest_data):
        log.error(
            f'ERROR: Comparison of current and past CRC data files shows that {past_data} has more data than {latest_data}'
            )
        raise TestException('FAIL: The past data set has more data than the current data set.')
    return latest_data, past_data


@pytest.mark.skip('Quarantined: See QX-5115 for further details')
@pytest.mark.sdi
@pytest.mark.parametrize('past_vers', _get_past_versions())
def test_crcs(nightly_data, past_vers):
    """
    Generates a set of NIGHTLY CRCs using the test Qx and then compares the resulting data against all the stored
    versions.
    """
    log.info(f'Using nightly test data file {nightly_data[0]}')
    latest_version = _latest_version()
    assert latest_version == nightly_data[1]
    latest_data, past_data = _check_data_size_valid(latest_version, past_vers)
    assert latest_data.equals(past_data)


@pytest.mark.skip('Quarantined: See QX-5115 for further details')
@pytest.mark.internal_test
@pytest.mark.sdi
@pytest.mark.parametrize('past_vers', _get_sad_test_versions())
def test_sad_crc_files(past_vers):
    """
    Check that the way we're comparing data is failing when it should to ensure that test_crcs() is a valid test.

    :params: current_data_file pd.core.frame.DataFrame
    :params: past_vers str
    """
    latest_version = _latest_version()
    if latest_version == past_vers:
        pytest.skip()

    with pytest.raises(TestException):
        latest_data, past_data_file = _check_data_size_valid(latest_version, past_vers)

        # Ensure that .equals here fails!
        assert not latest_data.equals(past_data_file)
