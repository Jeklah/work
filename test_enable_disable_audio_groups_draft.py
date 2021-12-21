"""
Tests to validate you can GET and SET the configuration for loudness
on Qx/QxL via REsT API.
"""
import os
import json
import time
import pytest
import logging
import requests
from random import randrange
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.qxexception import QxException
from test_system.testexception import TestException

# Set up logging for test_system
log = logging.getLogger(test_system_log)

# Setting up environment constants.
TEST = os.getenv("TEST_QX")
GENERATOR = os.getenv("GENERATOR_QX")
ANALYSER = os.getenv("ANALYSER_QX")

HEADERS = {
    "Content-type": "application/json"
}


def generate_command_data():
    """
    Generates data for the configuration of the Audio Groups.

    :returns command_data dict
    """
    group_check = {
        "audioGroup1": True,
        "audioGroup2": True,
        "audioGroup3": True,
        "audioGroup4": True,
        "audioGroup5": True,
        "audioGroup6": True,
        "audioGroup7": True,
        "audioGroup8": True
    }

    command_data = {"audioGroup": group_check}
    yield command_data


def make_SDI_unit(host):
    """
    Abstraction function for creating a Qx object supporting SDI or SDI Stress capabilities
    depending on lisences.

    :param host string
    :returns qx Object
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI_STRESS)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope="module")
def generator_qx(test_generator_hostname):
    """
    Creates Qx generator object using GENERATOR_QX env variable.

    :param test_generator_hostname String
    :returns generator_qx Object

    * Requests SDI capabilities, dependant on lisences.
    * Sets bouncing_box to False.
    * Sets output_copy to False.
    * Turns off jitter insertion.
    * Sets the SDI outputs to be generators.
    """
    generator_qx = make_SDI_unit(test_generator_hostname)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.generator.jitter_insertion("Disabled", 0.01, 10)
    generator_qx.io.set_sdi_outputs(
        ("generator", "generator", "generator", "generator")
    )
    log.info(f"FIXTURE: Qx {generator_qx.hostname} setup complete")
    yield generator_qx
    log.info(f"FIXTURE: Qx {generator_qx.hostname} teardown complete")


@pytest.fixture(scope="module")
def analyser_qx(test_analyser_hostname):
    """
    Creates a Qx object and configures it to be used as analyser.

    :param test_analyser_hostname String
    :returns analysr_qx Object
    """
    analyser_qx = make_SDI_unit(host=test_analyser_hostname)
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} setup complete.")
    yield analyser_qx
    log.info("Testing of enable/disable audio groups via REsT API complete.")
    log.info(f"Fixture: Qx {analyser_qx.hostname} teardown complete.")


def set_generator_standard(generator_qx, standard):
    """
    Sets the generator to a given standard.

    :param generator_qx Object
    :param standard tuple
    """
    resolution, mapping, gamut, test_pattern = standard
    # Set the generator to a standard compatible with 8 audio groups.
    generator_qx.generator.set_generator(
        resolution, mapping, gamut, test_pattern
    )

def preconfigure(qx_audio_url, command_data):
    audio_group_data = json.dumps(command_data)
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    preconfiguration = response.json()

    assert preconfiguration["status"] == 200


def set_get_configuration(qx_audio_url, audio_group_data):
    # Apply audio groups configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    # Get response.
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    return audio_group_results


def generate_standard_list():
    standards_list = [
        ('3840x2160p60', 'YCbCr:422:10', '12G_2-SI_Rec.709', '100% Bars'),

    ]
    for standard in standards_list:
        yield standard


def generate_qx_audio_url(generator_qx):
    """
    Sets and returns the URL for the API of audio generation.

    :return qx_audio_url string
    """
    qx_audio_url = f"http://{generator_qx.hostname}:8080/api/v1/generator/audio"
    return qx_audio_url


def generate_group_num_config():
    """
    Yield numbers 1-8 for use as index in configuring the audio groups.

    :return group int
    """
    for group in range(1, 9):
        yield group


def generate_audio_group_bool_config():
    """
    Yield the combinations of bool values to enable/disable the groups.

    :return val bool
    """
    for val in [True, False]:
        yield val


def generate_sad_audio_group_config():
    """
    NOTE:1 and 7 groups *should* be accepted but the current API fails. This is a known bug.
    Yield integers indicating how many/which groups are to be enabled for the sad
    audio group config testing.
    Test Cases:
        * 0 zero groups activated.
        * 1 one/AudioGroup1 activated.
        * 7 seven/AudioGroup1-7 activated.

    :return group int
    """
    for group in [0, 1, 7]:
        yield group


def generate_sad_audio_bool_config():
    """
    Yield combinations of bool which would be incorrect.
    """
    yield None


def generate_bad_json_audio_group_config():
    """
    Yield bad data for 'bad' input tests.
    """
    bad_json = {
        "aVeryBadly": {"formed_piece": "of_json", "that": "should_not_be_accepted"}
    }
    yield bad_json


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
@pytest.mark.parametrize("audio_group_bool_config", generate_audio_group_bool_config())
@pytest.mark.parametrize("audio_group_num_config", generate_group_num_config())
def test_enable_disable_single_audio_group(
    generator_qx, audio_group_num_config, audio_group_bool_config, command_data, standard
):
    """
    Tests the enabling and disabling of audio groups 1-8 individually.

    :param generator_qx Object
    :param audio_group_num_config int
    """
    # Set Generator
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Preconfigure
    preconfigure(qx_audio_url, command_data)

    # Set the command and expected audioGroup json results.
    group_check = command_data["audioGroup"]
    command_data["audioGroup"][f"audioGroup{audio_group_num_config}"] = audio_group_bool_config
    group_check[f"audioGroup{audio_group_num_config}"] = audio_group_bool_config
    audio_group_data = json.dumps(command_data)

    audio_group_results = set_get_configuration(qx_audio_url, audio_group_data)

    # Check the response status code came back as 200 (Success), otherwise fail the test.
    assert audio_group_results["status"] == 200

    # Check that the correct audio group was activated.
    assert group_check == audio_group_results["audioGroup"]


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
@pytest.mark.parametrize("audio_group_bool_config", generate_audio_group_bool_config())
def test_enable_disable_all_audio_groups(
    generator_qx, audio_group_bool_config, command_data, standard
):
    """
    Tests the enabling and disabling of all audio groups simultaneously.

    :param generator_qx Object
    :param audio_group_num_config int
    """

    # Set Generator
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    group_check = command_data["audioGroup"]
    for num in range(1, 9):
        command_data["audioGroup"][f"audioGroup{num}"] = audio_group_bool_config
        group_check[f"audioGroup{num}"] = audio_group_bool_config
    audio_group_data = json.dumps(command_data)

    # Apply audio groups configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    # Get response
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Check the response status code came back as 200 (Success), otherwise fail the test.
    assert audio_group_results["status"] == 200

    # Check that the correct audio group was activated.i
    assert group_check == audio_group_results["audioGroup"]

@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
def test_enable_multiple_random_audio_group(generator_qx, command_data, standard):
    """
    Test case to enable 2 randomly chosen audio groups.
    - Pre-condition: All audio groups are initially disabled.

    :param generator_qx Object
    :param command_data dict
    """
    # Set Generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set up pre-condition
    for grp_num in range(1, 9):
        command_data["audioGroup"][f"audioGroup{grp_num}"] = False

    # Set configuration
    group_check = command_data["audioGroup"]
    rand_audio_group_num_1 = randrange(1, 9)
    rand_audio_group_num_2 = randrange(1, 9)
    command_data["audioGroup"][f"audioGroup{rand_audio_group_num_1}"] = True
    command_data["audioGroup"][f"audioGroup{rand_audio_group_num_2}"] = True
    audio_group_data = json.dumps(command_data)

    time.sleep(1)  # Suspected ace condition/timing issue here. Tests failed when ran normally,
                   # but not while debugging. After a while I suspected timing being the cause
                   # as it was the only thing changing between running normally and debugging,
                   # thus the use of time.sleep(1) here, which seems to have resolved the issue.

    # Apply configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Check operation was successful
    assert audio_group_results['status'] == 200

    # Check configuration is what we expected
    assert group_check == audio_group_results['audioGroup']


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
def test_disable_multiple_audio_group(generator_qx, command_data, standard):
    """
    Test case to disable 2 randomly chosen audio groups simultaneously.

    :param generator_qx Object
    """
    # Set Generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    group_check = command_data["audioGroup"]
    rand_audio_group_num_1 = randrange(1, 9)
    rand_audio_group_num_2 = randrange(1, 9)
    command_data["audioGroup"][f"audioGroup{rand_audio_group_num_1}"] = False
    command_data["audioGroup"][f"audioGroup{rand_audio_group_num_2}"] = False
    audio_group_data = json.dumps(command_data)

    # Apply configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()
    time.sleep(1)

    # Check operation was successful
    assert audio_group_results['status'] == 200

    # Check configuration is what we expected
    assert group_check == audio_group_results['audioGroup']


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
def test_enable_8_to_4_audio_group(generator_qx, command_data, standard):
    """
    Test case for enabling 8 audio groups on a valid standard,
    then changing standard to one that only supports 4 audio groups
    to make sure the same configuration is still applied.

    :param generator_qx Object
    """
    # Set generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    group_check = command_data["audioGroup"]
    audio_group_data = json.dumps(command_data)

    time.sleep(1)

    # Apply audio groups configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    time.sleep(1)

    # Check operation was successful
    assert audio_group_results['status'] == 200

    # Check configuration is what we expected
    assert group_check == audio_group_results['audioGroup']

    # Set generator to standard known to support 4 Audio Groups.
    generator_qx.generator.set_generator("1920x1080p50", "YCbCr:422:10", "DL_1.5G_Rec.709", "100% Bars")

    # Set group_check to what would be the valid configuration to check against for 4 Audio Groups
    for num in range(5, 9):
        group_check[f"audioGroup{num}"] = False

    time.sleep(1)

    # Apply audio groups configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Check operation was successful
    assert audio_group_results['status'] == 200

    # Check configuration is what we expected
    assert group_check == audio_group_results['audioGroup']

@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
def test_disable_multiple_random_audio_group(generator_qx, command_data, standard):
    """
    Test case to disable a randomly chosen audio group.

    :param generator_qx Object
    :param audio_group_bool_config bool
    """
    # Set generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set pre-condition (because last test required 4 groups enabled, the Qx will still
    # be configured like this, so reconfigure, enable all groups again.
    requests.put(qx_audio_url, headers=HEADERS, data=json.dumps(command_data))
    time.sleep(1)
    res = requests.get(qx_audio_url, headers=HEADERS)
    config_data = res.json()
    assert config_data['status'] == 200

    # Set configuration
    group_check = command_data["audioGroup"]
    rand_audio_group_num = randrange(1, 9)
    command_data["audioGroup"][f"audioGroup{rand_audio_group_num}"] = False
    group_check[f"audioGroup{rand_audio_group_num}"] = False
    audio_group_data = json.dumps(command_data)

    # Apply configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Check the operation was successful.
    assert response.status_code == 200

    # Check the configuration is what we expect.
    assert group_check == audio_group_results["audioGroup"]


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
def test_enable_4_to_2_from_8_audio_groups(generator_qx, command_data, standard):
    """
    Test case to check you can switch from 4 audio groups being enabled in
    a standard valid for up to 8 audio groups, to a standard that only supports
    2 audio groups and the configuration still holds up correctly.

    :param generator_qx Object
    :param command_data dict
    """
    # Set generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    for val in range(5, 9):
        command_data["audioGroup"][f"audioGroup{val}"] = False
    group_check = command_data["audioGroup"]
    audio_group_data = json.dumps(command_data)

    # Apply audio groups configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(2)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Check operation was successful
    assert audio_group_results['status'] == 200

    # Check assignment of 4 Audio Groups on a standard that supports 8 Audio Groups is successful.
    assert group_check == audio_group_results["audioGroup"]
    # print('4 Audio Groups on 8 compatible std done.')

    # Set generator to standard known to only support 2 Audio Groups.
    generator_qx.generator.set_generator('2048x1080p60', 'YCbCr:422:10', 'DL_1.5G_Rec.709', '100% Bars')

    # Set configuration
    group_check = command_data["audioGroup"]
    for num in range(1, 9):
        command_data["audioGroup"][f"audioGroup{num}"] = True
        group_check[f"audioGroup{num}"] = True
    audio_group_data = json.dumps(command_data)

    # Apply configuration
    requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)
    response = requests.get(qx_audio_url, headers=HEADERS)
    audio_group_results = response.json()

    # Set expected results
    for num in range(3, 9):
        group_check[f"audioGroup{num}"] = False

    # Check the operation was successful.
    assert response.status_code == 200

    # Check the configuration is what we expect.
    assert group_check == audio_group_results["audioGroup"]


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
@pytest.mark.parametrize("sad_audio_bool_config", generate_sad_audio_bool_config())
def test_enable_disable_sad_audio_groups_value(generator_qx, sad_audio_bool_config, command_data, standard):
    """
    Tests configuring the audio groups one by one with one of the groups having an invalid setting
    or group number.

    :param generator_qx Object
    :param sad_audio_group_config list
    """
    # Set generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    group_check = command_data["audioGroup"]
    for num in range(1, 9):
        command_data["audioGroup"][f"audioGroup{num}"] = sad_audio_bool_config
        group_check[f"audioGroup{num}"] = sad_audio_bool_config
    audio_group_data = json.dumps(command_data)

    # Set audio groups configuration
    response = requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)

    # Check the response is a 400
    # 400 for a non-boolean value being compared, i.e 'NoneType'.
    assert response.status_code == 400


@pytest.mark.sdi
@pytest.mark.parametrize("standard", generate_standard_list())
@pytest.mark.parametrize("command_data", generate_command_data())
@pytest.mark.parametrize("sad_audio_group_config", generate_sad_audio_group_config())
def test_enable_disable_sad_audio_groups(generator_qx, sad_audio_group_config, command_data, standard):
    """
    Test to make sure that invalid audio groups are reported as being invalid.

    :param generator_qx Object
    :param sad_audio_group_config list
    :param command_data dict
    """

    # Set generator to standard known to support 8 Audio Groups.
    set_generator_standard(generator_qx, standard)

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Set configuration
    if sad_audio_group_config == 1:
        command_data = {"audioGroup": {"audioGroup1": True}}
    elif sad_audio_group_config == 7:
        command_data = {
            "audioGroup": {
                "audioGroup1": True,
                "audioGroup2": True,
                "audioGroup3": True,
                "audioGroup4": True,
                "audioGroup5": True,
                "audioGroup6": True,
                "audioGroup7": True,
            }
        }
    else:
        command_data = {"audioGroup": {}}

    audio_group_data = json.dumps(command_data, separators=(",", ":"))

    # Set audio groups configuration
    response = requests.put(qx_audio_url, headers=HEADERS, data=audio_group_data)
    time.sleep(1)

    # Check the response is a 400.
    # 400 for bad request client error status.
    assert response.status_code == 400


@pytest.mark.sdi
@pytest.mark.parametrize("bad_json", generate_bad_json_audio_group_config())
def test_enable_disable_bad_audio_groups(generator_qx, bad_json):
    """
    Generates some bad data to be sent for bad input tests.

    :param generator_qx Object
    :param bad_json dict
    """

    # Set REsT API Audio URL
    qx_audio_url = generate_qx_audio_url(generator_qx)

    # Send invalid configuration
    response = requests.put(qx_audio_url, headers=HEADERS, data=bad_json)
    time.sleep(1)

    # Check the response is 415
    # 415 for unsupported media type client error/ body not recognised as JSON.
    assert response.status_code == 415
