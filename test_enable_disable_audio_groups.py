"""
Tests to validate you can enable / disable audio groups for loudness
on Qx/QxL via ReST API.
"""
import time
import pytest
import logging
from test_system.factory import make_qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.qxexception import QxException

# Set up logging for test_system
log = logging.getLogger(test_system_log)

HEADERS = {
    "Content-type": "application/json"
}

def generate_command_data():
    """
    Returns a dictionary for the enable or disable of the Audio Groups.

    :returns dict
    """
    command_data = {
        "audioGroup1": True,
        "audioGroup2": True,
        "audioGroup3": True,
        "audioGroup4": True,
        "audioGroup5": True,
        "audioGroup6": True,
        "audioGroup7": True,
        "audioGroup8": True
    }
    return command_data


def make_SDI_unit(host):
    """
    Abstraction function for creating Qx object supporting SDI
    depending on licenses.

    :param host string
    :returns Object
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates Qx generator object using GENERATOR_QX env variable.

    :param test_generator_hostname string
    :returns object

    * Requests SDI capabilities, dependant on licences.
    * Sets the SDI outputs to be the generators.
    """
    generator_qx = make_SDI_unit(test_generator_hostname)
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    preconfigure(generator_qx, generate_command_data())
    log.info(f'FIXTURE: Qx {generator_qx.hostname} setup complete.')
    yield generator_qx
    # Set all audio groups to enabled after each test.
    preconfigure(generator_qx, generate_command_data())
    log.info(f'FIXTURE: Qx {generator_qx.hostname} teardown complete.')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    """
    Creates a Qx object and configures it to be used as analyser.

    :param test_analyser_hostname
    :returns object
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete.')
    yield analyser_qx
    log.info('Testing of enable/disable audio groups via ReST API complete.')
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete.')


def preconfigure(generator_qx, command_data):
    """
    Preconfigures the audio groups to be all enabled at the start of the test.

    :param generator_qx object
    :param command_data dict
    """
    try:
        generator_qx.generator.audio_group = command_data
    except QxException as audio_group_err:
        log.error(f'Qx {generator_qx.hostname}: An error occurred while enabling/disabling the audio groups: {audio_group_err}')


def generate_standard_list():
    """
    Iterates through a list of standards to test audio groups with.

    :returns tuple
    """
    standards_list = [
        ('3840x2160p60', 'YCbCr:422:10', '12G_2-SI_Rec.709', '100% Bars'),
        ('2048x1080p50', 'YCbCr:422:10', '3G_A_Rec.709', '100% Bars'),
        # ('1920x1080p29.97', 'RGB:444:10', '3G_A_Rec.709', '100% Bars'),
        # ('1920x1080psf29.97', 'YCbCr:444:10', '3G_B_Rec.709', '100% Bars'),
        # ('1920x1080i50', 'YCbCr:422:12', '3G_B_Rec.2020', '100% Bars'),
        # ('1920x1080i60', 'RGB:444:12', '3G_B_Rec.709', '100% Bars')
    ]
    for standard in standards_list:
        yield standard


def generate_audio_group_index():
    """
    Yield numbers 1-8 for use as index in configuring the audio groups.

    :return int
    """
    for index in range(1, 9):
        yield index


def generate_audio_group_bool_value():
    """
    Yield both True and False values to enable/disable the audio groups.

    :return bool
    """
    for val in [True, False]:
        yield val


@pytest.mark.sdi
@pytest.mark.parametrize("audio_group_bool_value", generate_audio_group_bool_value())
@pytest.mark.parametrize("audio_group_index_value", generate_audio_group_index())
@pytest.mark.parametrize("standard", generate_standard_list())
def test_enable_disable_single_audio_group(
    generator_qx, standard, audio_group_index_value, audio_group_bool_value
):
    """
    Tests the enabling and disabling of audio groups 1-8 individually.

    :param generator_qx object
    :param audio_group_index_value int
    :param audio_group_bool_value bool
    :param standard tuple
    """
    preconfigure(generator_qx, generate_command_data())
    generator_qx.generator.set_generator(*standard)
    command_data = generate_command_data()
    preconfigure(generator_qx, generate_command_data())

    # Set expected JSON and command to send
    command_data[f"audioGroup{audio_group_index_value}"] = audio_group_bool_value
    group_check = command_data

    # Apply command
    generator_qx.generator.audio_group = command_data
    time.sleep(1)
    curr_audio_group_state = generator_qx.generator.audio_group

    assert group_check == curr_audio_group_state
