"""
Tests to validate you can enable / disable audio groups for loudness
on Qx/QxL via ReST API.
NOTE: This test only checks via the ReST API and does not use an analyser to check
      whether the Qx actually disables/enables the audio groups.
"""
import time
import pytest
import logging
from typing import Generator as Generator
from autolib.factory import make_qx, Qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qxexception import QxException

# Set up logging for autolib
log = logging.getLogger(autolib_log)

HEADERS = {
    "Content-type": "application/json"
}


def generate_command_data() -> dict:
    """
    Returns a dictionary for the enable or disable of the Audio Groups.

    :return: dict
    """
    return {"audioGroup1": True,
            "audioGroup2": True,
            "audioGroup3": True,
            "audioGroup4": True,
            "audioGroup5": True,
            "audioGroup6": True,
            "audioGroup7": True,
            "audioGroup8": True
            }


def make_sdi_unit(host: str) -> Qx:
    """
    Construct a Qx series device configured to operate in SDI mode with SDI outputs
    set to use the BNC connectors.

    :param host: String containing hostname or IPv4 of Qx series device.
    :return: Qx
    """
    qx = make_qx(host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates Qx generator object configured to operate in SDI mode with SDI outputs
    set to use the BNC connectors.

    :param test_generator_hostname: String containing hostname or IP of test unit.
    :return: Qx

    * Requests SDI capabilities, dependent on licences.
    * Sets the SDI outputs to be the generators.
    """
    generator_qx = make_sdi_unit(test_generator_hostname)
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    pre_test_setting = generator_qx.generator.audio_group
    generator_qx.generator.audio_group = generate_command_data()
    log.info(f'FIXTURE: Qx {generator_qx.hostname} setup complete.')
    yield generator_qx
    generator_qx.generator.audio_group = pre_test_setting
    log.info(f'FIXTURE: Qx {generator_qx.hostname} teardown complete.')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates Qx analyser object configured to operate in SDI mode with SDI outputs
    set to use the BNC connectors.

    :param test_analyser_hostname: String containing hostname or IP of test unit.
    :return: Qx
    """
    analyser_qx = make_sdi_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete.')
    yield analyser_qx
    log.info('Testing of enable/disable audio groups via ReST API complete.')
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete.')


def config_audio_groups(generator_qx: Qx, command_data: dict) -> None:
    """
    Configs the audio groups to be all enabled at the start of the test.

    :param generator_qx: Qx
    :param command_data: Dictionary containing config to set all audio groups to enabled.
    """
    try:
        generator_qx.generator.audio_group = command_data
    except QxException as audio_group_err:
        log.error(
            f'Qx {generator_qx.hostname}: An error occurred while enabling/disabling the audio groups: {audio_group_err}')


def generate_standard_list() -> Generator[tuple, None, None]:
    """
    Iterates through a list of standards to test audio groups with.

    :return: Tuple containing the details of a standard in the form:
        ('resolution', 'mapping', 'gamut', 'test_pattern')
    """
    yield from [
        ('3840x2160p60', 'YCbCr:422:10', '12G_2-SI_Rec.709', '100% Bars'),
        ('2048x1080p50', 'YCbCr:422:10', '3G_A_Rec.709', '100% Bars'),
    ]


def generate_audio_group_index() -> Generator[int, None, None]:
    """
    Yield numbers 1-8 for use as index in configuring the audio groups.

    :return: Returns an integer to be used as index for audio groups.
    """
    yield from range(1, 9)


def generate_audio_group_bool_value() -> Generator[bool, None, None]:
    """
    Yield both True and False values to enable/disable the audio groups.

    :return: Returns a bool value used to enable/disable audio groups.
    """
    yield from [True, False]


@pytest.mark.sdi
@pytest.mark.parametrize("audio_group_bool_value", generate_audio_group_bool_value())
@pytest.mark.parametrize("audio_group_index_value", generate_audio_group_index())
@pytest.mark.parametrize("standard", generate_standard_list())
def test_enable_disable_single_audio_group(
        generator_qx: Qx, standard: tuple, audio_group_index_value: int, audio_group_bool_value: bool
):
    """
    Tests the enabling and disabling of audio groups 1-8 individually.

    :param generator_qx: Qx
    :param standard: Details of a standard in the form:
           ('resolution', 'mapping', 'gamut', 'test_pattern')

    :param audio_group_index_value: Index for audio_groups.
    :param audio_group_bool_value: Value for audio_groups to be set to.
    """
    generator_qx.generator.set_generator(*standard)
    time.sleep(2)
    if generator_qx.generator.is_generating_standard(*standard) is False:
        time.sleep(2)
    config_audio_groups(generator_qx, generate_command_data())
    command_data = generate_command_data()

    # Set expected JSON and command to send
    command_data[f"audioGroup{audio_group_index_value}"] = audio_group_bool_value
    group_check = command_data

    # Apply command
    generator_qx.generator.audio_group = command_data
    curr_audio_group_state = generator_qx.generator.audio_group

    assert group_check == curr_audio_group_state
