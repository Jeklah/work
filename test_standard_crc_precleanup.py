"""
The test that checks the CRCs generated for each test patterns have not changed
in the past 2 releases/versions.

This implementation of the test takes the df for a standard, all its test patterns
and CRCs and compares it with the same df taken from a different version.
This speeds up the test significantly as it does not require the Qx to be generating
live while running the tests.
"""
import ast
import logging
import pathlib
import re
import sys

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

import pandas as pd
import pytest
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.testexception import TestException


log = logging.getLogger(test_system_log)


@pytest.fixture(scope="module")
def test_qx(test_generator_hostname):
    yield make_qx(hostname=test_generator_hostname)


@pytest.fixture(scope="module")
def current_version(test_qx):
    yield test_qx.about.get("Software_version", None)


@pytest.fixture(scope="module")
def current_data_file(current_version):
    data_path = pathlib.Path(__file__).parent / "crc_data"
    current_version_file = data_path / f"crcRecord-nightly-{current_version}.json"
    if current_version_file.exists():
        current_data = pd.read_json(current_version_file, orient="table")
        yield current_data
    else:
        raise TestException(
            f"Could not read JSON data file for current build version {current_version}."
        )


def _get_past_versions():
    """
    Get a list of the versions for which JSON files exist in the crc_data folder that match:

        crcRecord-nightly-<x.y.z>.json

    """
    mod_path = pathlib.Path(__file__).parent / "crc_data"
    versions = []
    for jsonfile in mod_path.glob("*.json"):
        match = re.search(
            r"crcRecord-nightly-(?P<fw_ver>\d{1,4}\.\d{1,4}\.\d{1,4}).json",
            jsonfile.name,
        )
        if match:
            versions.append(match.group("fw_ver"))
    return list(versions)


def _read_last_results_json(past_version):
    """
    This reads the last known test results from JSON files.

    Parameters:
        * past_version string
    """
    data_path = pathlib.Path(__file__).parent / "crc_data"
    past_version_file = data_path / f"crcRecord-nightly-{past_version}.json"
    if past_version_file.exists():
        with open(past_version_file) as past_version_json:
            past_version_data = ast.literal_eval(past_version_json.read())
            crc_data = past_version_data["data"]
            metadata = past_version_data["metadata"]
            log.info(f"Loaded store crc dataframe with metadata: {metadata}")
        return pd.DataFrame.from_dict(crc_data)
    else:
        raise TestException(f"Could not read JSON data file for version {past_version}")


# NOTE: Shape does not need to be checked due to .equals handling
#       as long as the columns are the same, which they will be as
#       the JSON column names are defined within the tests.
#       What DOES need to be checked is whether the current version
#       has less data than the past version (FAIL) as well as
#       if the current version has more data (PASS but must log discrepancy).


@pytest.mark.sdi
@pytest.mark.parametrize("past_vers", _get_past_versions())
def check_data_size_equality(current_data_file, past_vers):
    past_data = _read_last_results_json(past_vers)
    if len(current_data_file) > len(past_data):
        log.info(
            f"Comparison of current and past CRC data files shows that {current_data_file} has more data than {past_data}"
        )
        pass
    elif len(past_data) > len(current_data_file):
        log.error(
            f"ERROR: Comparison of current and past CRC data files shows that {past_data} has more data than {current_data_file}"
        )
        pytest.fail(
            msg="FAIL: The past data set has more data than the current data set.",
            pytrace=True,
        )
        return False
    else:
        return True


@pytest.mark.sdi
@pytest.mark.parametrize("past_vers", _get_past_versions())
def test_crcs(current_data_file, past_vers):
    """
    Compares CRCs of all test_patterns for a standard to previous versions.

    Parameters:
        * test_qx object
        * current_data_file json
        * past_vers string
    """
    past_data_file = _read_last_results_json(past_vers)
    assert current_data_file.equals(past_data_file[["Standard", "Pattern", "CrcValue", "CrcCount"]])


####################################


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
        input_lines = loader.read().splitlines()

    loaded_stds = []
    for line in input_lines:
        if line == "":
            continue
        loaded_stds.append(line.split(","))

    return loaded_stds

# def get_past_versions(current_version):
#     """
#     Yield past versions to test against.
#     """
#     versions = [
#         "4.3.1",
#         "4.4.0",
#         "4.5.0",
#     ]
#     try:
#         if current_version not in versions:
#             log.error(f'An error has occurred: There is no data file for version {current_version}.')
#     except TestException as no_crc_data_err:
#         log.error(f'An error has occurred: {no_crc_data_err}. There is no datafile for {current_version}.')
#     for vers in versions:
#         yield vers


# def read_last_test_results_pickle(generator_qx, past_vers=get_past_versions()):
#     """
#     This reads the last known test results from pickle files.
#     Keeping this function as the test actually performs better when
#     comparing pkl files rather than json files.
#
#     Parameters:
#         * generator_qx object
#         * past_vers string
#     """
#     curr_vers = generator_qx.about["Software_version"]
#     try:
#         if os.path.exists(f"./crcRecord-nightly-{past_vers}.pkl"):
#             return (
#                 pd.read_pickle(f"./CRC_Checks/crcRecord-nightly-{curr_vers}.pkl"),
#                 curr_vers,
#                 pd.read_pickle(f"./CRC_Checks/crcRecord-nightly-{past_vers}.pkl"),
#             )
#         else:
#             return pd.read_pickle(
#                 f"./CRC_Checks/crcRecord-nightly-{curr_vers}.pkl"
#             ), pd.read_pickle("./CRC_Checks/crc_corr_check.pkl")
#     except FileNotFoundError as ferr:
#         log.error(f"The file for a previous version could not be found. {ferr}")


# def read_last_test_results_json(generator_qx, past_vers=get_past_versions()):
#     """
#     This reads the last known test results from json files.
#
#     Parameters:
#         * generator_qx object
#         * past_vers string
#     """
#     curr_vers = generator_qx.about["Software_version"]
#     try:
#         if os.path.exists(f"./CRC_Checks/crcRecord-nightly-{past_vers}.json"):
#             return (
#                 pd.read_json(
#                     f"./CRC_Checks/crcRecord-nightly-{curr_vers}.json", orient="table"
#                 ),
#                 curr_vers,
#                 pd.read_json(
#                     f"./CRC_Checks/crcRecord-nightly-{past_vers}.json", orient="table"
#                 ),
#             )
#     except FileNotFoundError as ferr:
#         log.error(f"The file for the previous version could not be found. {ferr}")


# @pytest.mark.sdi
# @pytest.mark.parametrize("past_vers", get_past_versions())
# def test_crcs(generator_qx, confidence_test_standards, past_vers):
#     """
#     Compares CRCs of all test_patterns for a standard to previous versions.
#
#     Parameters:
#         * generator_qx object
#         * confidence_test_standards tuple
#         * past_vers string
#     """
#     std = confidence_test_standards
#     todays_results, curr_vers, recent_results = read_last_test_results_json(
#         generator_qx, past_vers
#     )
#     # todays_results, curr_vers, recent_results = read_last_test_results_pickle(generator_qx, past_vers)
#     standard_df = todays_results.loc[todays_results["Standard"] == std]
#
#     try:
#         pattern_index_list = []
#         for index in standard_df["Pattern"].index:
#             pattern_index_list.append(index)
#
#     except TestException as terr:
#         log.error(f"The standard could not be found: {terr}")
#     test_patterns = standard_df["Pattern"].values.tolist()
#
#     # get crcs for the standard being tested.
#     # they will be in the same order as the test pattern list, so they can use the same index.
#     crc_list = standard_df["CrcValue"].values.tolist()
#
#     print(f"Checking standard: {std}, versions: {curr_vers} against {past_vers} ")
#     for patt, crc in zip(test_patterns, crc_list):
#         assert recent_results[(recent_results["Standard"] == std)].equals(
#             todays_results[(todays_results["Standard"] == std)]
#         )
#         tmp_df = recent_results[["Standard", "Pattern", "CrcValue"]]
#         test_pattern_crc_df = tmp_df[tmp_df["Standard"] == std]
#
#         todays_tmp_df = todays_results[["Standard", "Pattern", "CrcValue"]]
#         todays_test_pattern_crc_df = todays_tmp_df[todays_tmp_df["Standard"] == std]
#
#         assert todays_test_pattern_crc_df.equals(test_pattern_crc_df)
