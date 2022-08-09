"""\
Tests to validate the loudness monitoring is accurate to 0.01 +- 0.01 for stereo audio.
"""
import pytest
import logging
import shutil
import time
import os
import paramiko
from collections.abc import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def yield_gain_values() -> Generator[float, None, None]:
    """
    Yields the values to be used for gain.

    :return: float
    """
    yield from [-23.0, -33.0]


def stereo_loudness_settings() -> dict:
    """
    Provides the loudness settings in JSON format.

    :return: Configuration for the loudness settings to start off with.
    """
    return {"channels": [
        {"channel": 0, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 1, "frequency_Hz": 1000, "gain_dBFS": 0},
    ]}


def channel_assignment() -> dict:
    """
    Provides the JSON required for channel assignment in the tests.

    :return: Channel assignment configuration for stereo setup.
    """
    return {"audioAssignment": {
            "audioMode": "stereo",
            "channelAssignment": {
                "left": {
                    "channel": "group1Pair1Left",
                    "subimage": 1
                },
                "right": {
                    "channel": "group1Pair1Right",
                    "subimage": 1
                }
            }}}


def make_SDI_unit(host: str) -> Qx:
    """
    Function for creating Qx objects that support SDI.

    :param host: Hostname or IP of the unit under test.
    :return: Qx configured for SDI use.
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope="module")
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx generator object.

    :param test_generator_hostname: str
    :return: Qx object to be used as the generator.
    """
    gen_qx = make_SDI_unit(test_generator_hostname)
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"FIXTURE: Qx {gen_qx.hostname} setup complete.")
    yield gen_qx
    log.info(f"FIXTURE: Qx {gen_qx.hostname} teardown complete.")


@pytest.fixture(scope="module")
def analyser_qx(test_analyser_hostname) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyser.

    :param test_analyser_hostname: string
    :return: Qx object to be used as the analyser.
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f"FIXTURE: Qx {analyser_qx.ip} setup complete")
    yield analyser_qx
    log.info(f"FIXTURE: Qx {analyser_qx.ip} teardown complete")
    remove_extracted_logs()


def _generate_loudness_standard() -> Generator[str, None, None]:
    """
    Generate valid values for the loudness standard.

    :param analyser_qx: Qx object used to represent the unit being used as the analyser.
    :return: Value used to set the loudness standard.
    """
    yield from ['ebuLu', 'ebuLufs']


def start_stop_loudness(analyser_qx: Qx) -> None:
    """
    Starts and stops the loudness monitor between tests.

    NOTE: This could be refined by only sending the payload containing the necessary data,
          i.e the control value. It would be interesting to see how much quicker this improvement
          would make the test runs.
          Since this don't need this refinement immediately it has not been implemented, but it is
          something to consider in the future.

    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    """
    loudness_control = analyser_qx.analyser.loudness_config
    loudness_control["control"] = 'start'
    analyser_qx.analyser.loudness_config = loudness_control
    time.sleep(20)
    loudness_control["control"] = 'stop'
    analyser_qx.analyser.loudness_config = loudness_control


def remove_old_logs() -> None:
    """
    Removes loudness_logs.zip after each test.
    """
    os.remove('./loudness_logs.zip')


def remove_extracted_logs() -> None:
    """
    Removes the extracted_logs directory after each test.
    """
    shutil.rmtree('extracted_logs/')


def connect_and_unpack(analyser_qx: Qx) -> None:
    """
    Gets the loudness logs for the current test.

    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    """
    password = 'PragmaticPhantastic'
    username = 'root'
    with paramiko.SSHClient() as ssh:
        get_loudness_logs(ssh, analyser_qx, username, password)
    shutil.unpack_archive('./loudness_logs.zip', 'extracted_logs')
    remove_old_logs()


def get_loudness_logs(ssh: paramiko.SSHClient, analyser_qx: Qx, username: str, password: str):
    """
    Connects to the qx unit being used as the analyser and saves the loudness logs zip
    file

    :param ssh: paramiko.client.SSHClient object used to connect.
    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    :param username: string username for use in ssh.
    :param password: string password for user in ssh.
    """
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(analyser_qx.ip, username=username, password=password)
    sftp = ssh.open_sftp()
    sftp.chdir('/home/sftp/qxuser/transfer/log/loudness/')
    log_list = sftp.listdir()
    log_list.sort()
    latest_log = log_list[-1]
    log_path = f'/home/sftp/qxuser/transfer/log/loudness/{latest_log}'.strip('\n')
    sftp.get(log_path, './loudness_logs.zip')


def read_most_recent_log() -> str:
    """
    Return the most recent .txt file from the unzipped logs in extracted_logs dir.

    :return: string
    """
    return os.popen("cd extracted_logs/; ls -Art *.txt | tail -n 1").read().replace('\n', '')


def is_in_range(assess_value, lower, upper):
    """
    Checks if a given value is within lower and upper boundaries.

    :param assess_value: float Value to be checked if it is in range.
    :param lower: float Value for the lower limits of the range.
    :param upper: float Value for the upper limits of the range.
    """
    return assess_value >= lower and assess_value <= upper


@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard())
@pytest.mark.parametrize('gain', yield_gain_values())
def test_momentary(generator_qx: Qx, analyser_qx: Qx, gain: float, loudness_standard: str):
    """
    Set a tone and then check that the tone being recorded by the loudness
    monitor is accurate to what we set it within 0.01 LU.

    :param generator_qx: Qx
    :param analyser_qx: Qx
    :param gain: float
    :param loudness_standard: str
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    stereo_loudness = stereo_loudness_settings()
    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = gain
    analyser_qx.analyser.loudness_config = channel_assignment()
    generator_qx.generator.audio_custom_config = stereo_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness log on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    momentary_peak_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Momentary Peak: '").read().replace('\n', '')
    momentary_peak_value = float(momentary_peak_str.lstrip('Momentary Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(momentary_peak_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(momentary_peak_value, -10.0 - 0.1, -10.0 + 0.1)


@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard())
@pytest.mark.parametrize('gain', yield_gain_values())
def test_short_term(generator_qx, analyser_qx, gain, loudness_standard):
    """
    Set a tone and then check that the tone being recorded by the loudness
    monitor is accurate to what we set it within 0.01 LU.

    :param generator_qx: object
    :param analyser_qx: object
    :param gain: int
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    stereo_loudness = stereo_loudness_settings()
    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = gain
    analyser_qx.analyser.loudness_config = channel_assignment()
    generator_qx.generator.audio_custom_config = stereo_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness log on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    short_term_peak_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Short Term Peak: '").read().replace('\n', '')
    short_term_peak_value = float(short_term_peak_str.lstrip('Short Term Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(short_term_peak_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(short_term_peak_value, -10.0 - 0.1, -10 + 0.1)


@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard())
@pytest.mark.parametrize('gain', yield_gain_values())
def test_integrated(generator_qx, analyser_qx, gain, loudness_standard):
    """
    Set a tone and then check that the tone being recorded by the loudness
    monitor is accurate to what we set it within 0.01 LU.

    :param generator_qx: object
    :param analyser_qx: object
    :param gain: int
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    stereo_loudness = stereo_loudness_settings()
    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = gain
    analyser_qx.analyser.loudness_config = channel_assignment()
    generator_qx.generator.audio_custom_config = stereo_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness log on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    integrated_peak_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Integrated Peak: '").read().replace('\n', '')
    integrated_peak_value = float(integrated_peak_str.lstrip('Integrated Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(integrated_peak_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(integrated_peak_value, -10.0 - 0.1, -10 + 0.1)
