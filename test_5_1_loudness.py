"""
Tests to validate the loudness monitoring is accurate to 0.01 +- 0.01 for 5.1 audio.
"""
import pytest
import logging
import shutil
import time
import os
import paramiko
from paramiko.client import SSHClient
from collections.abc import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def yield_gain_values() -> Generator[float, None, None]:
    """
    Yield valid values to be used in the test.

    :return: float
    """
    yield from [-23.0, -33.0]


def fiveone_loudness_settings() -> dict:
    """
    Returns a basic channel set up config for 5.1.

    :return: A basic JSON configuration for channel set up for 5.1 audio.
    """
    return {"channels": [
        {"channel": 0, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 1, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 2, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 3, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 4, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 5, "frequency_Hz": 1000, "gain_dBFS": 0},
    ]}


# def channel_assignment() -> dict:
#     """
#     Returns a basic Channel Assignment JSON configuration for 5.1.
# 
#     :return: Basic Channel Assignment in JSON format for 5.1.
#     """
#     return {"audioAssignment": {
#             "audioMode": "5.1",
#             "channelAssignment": {
#                 "centre": {
#                     "channel": 3,
#                     "flow": 1
#                 },
#                 "left": {
#                     "channel": 1,
#                     "flow": 1
#                 },
#                 "leftSurround": {
#                     "channel": 5,
#                     "flow": 1
#                 },
#                 "lfe": {
#                     "channel": 4,
#                     "flow": 1
#                 },
#                 "right": {
#                     "channel": 2,
#                     "flow": 1
#                 },
#                 "rightSurround": {
#                     "channel": 6,
#                     "flow": 1
#                 }
#             }}}


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


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Setup/teardown fixture for generator_qx.

    :param test_generator_hostname: Hostname of unit to be used as generator.
    :return: Generator to provde Qx objects to be used as the generator for a test.
    """
    gen_qx = make_SDI_unit(host=test_generator_hostname)
    log.info(f'FIXTURE: Qx {gen_qx.hostname} setup complete')
    yield gen_qx
    log.info(f'FIXTURE: Qx {gen_qx.hostname} teardown complete')


@pytest.fixture(scope="module")
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Setup/teardown fixture for analyser_qx.

    :param test_analyser_hostname: Hostname of unit to be used as analyser.
    :return: Generator to provide Qx objects to be used as the analyser for a test.
    """
    analyser_qx = make_SDI_unit(host=test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete')
    yield analyser_qx
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete')


def _generate_gain_formatter(args: float) -> str:
    """
    Format test IDs for the gain value.
    :param args: Value of gain to be formatted for the test ID.
    :return: String value of gain.
    """
    gain = args
    return f'Gain value is: {gain}'


def _generate_loudness_standard_formatter(args: str) -> str:
    """
    Format test IDs for the loudness standard.
    :param args: Value of loudness_standard to be formatted for the test ID.
    :return: String value of the loudness_standard.
    """
    loudness_standard = args
    return f'Loudness Standard: {loudness_standard}'


def _generate_loudness_standard() -> Generator[str, None, None]:
    """
    Generate valid values for the loudness standard.

    :param analyser_qx: Qx object to be used to represent the unit being used as the analyser.
    :return: Value used to set the loudness standard.
    """
    yield from ['ebuLu', 'ebuLufs']


def start_stop_loudness(analyser_qx: Qx) -> None:
    """
    Start the loudness monitor, wait 20s, then stop the loudness monitor.

    :param analyser_qx: Qx object to be used as the analyser in this test.
    """
    loudness_control = analyser_qx.analyser.loudness_config
    loudness_control["control"] = 'start'
    analyser_qx.analyser.loudness_config = loudness_control
    # duration of the tests
    time.sleep(20)
    loudness_control["control"] = 'stop'
    analyser_qx.analyser.loudness_config = loudness_control


def remove_old_logs() -> None:
    """Removes old logs"""
    os.remove('./loudness_logs.zip')


def remove_extracted_logs() -> None:
    """Remove extracted logs"""
    shutil.rmtree('extracted_logs/')


def connect_and_unpack(analyser_qx: Qx) -> None:
    """
    Connect to analyser_qx and unpack the logs to extracted_logs dir.

    :param analyser_qx: Qx object to be used as the analyser for this test.
    """
    password = 'PragmaticPhantastic'
    username = 'root'
    with SSHClient() as ssh:
        get_loudness_logs(ssh, analyser_qx, username, password)
    shutil.unpack_archive('./loudness_logs.zip', 'extracted_logs')
    remove_old_logs()


def get_loudness_logs(ssh: SSHClient, test_unit: Qx, username: str, password: str) -> None:
    """
    Get the loudness logs from the provided test unit.
    """
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(str(test_unit.ip), username=username, password=password)
    sftp = ssh.open_sftp()
    sftp.chdir('/home/sftp/qxuser/transfer/log/loudness/')
    log_list = sftp.listdir()
    log_list.sort()
    latest_log = log_list[-1]
    log_path = f'/home/sftp/qxuser/transfer/log/loudness/{latest_log}'.strip('\n')
    sftp.get(log_path, './loudness_logs.zip')


def read_most_recent_log() -> str:
    """
    Reads the most recent log file.

    :return: contents of most recent log file.
    """
    return os.popen('cd extracted_logs/; ls -Art *.txt | tail -n 1').read().replace('\n', '')


def is_in_range(assess_value: float, lower: float, upper: float) -> bool:
    """
    Checks if a given value is within a given range.

    :param assess_value: value to be checked.
    :param lower: lower end of the range to be checked.
    :param upper: upper end of the range to be checked.
    :return: true or false depending on whether the value is within the aforementioned range.
    """
    return lower <= assess_value <= upper


@pytest.mark.parametrize('gain', yield_gain_values(), ids=_generate_gain_formatter)
@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard(), ids=_generate_loudness_standard_formatter)
def test_5_1_momentary(generator_qx: Qx, analyser_qx: Qx, gain: float, loudness_standard: str) -> None:
    """
    Test momentary values for 5.1 audio settings in loudness monitoring.

    :param generator_qx: Qx object to be used as a generator for the test suite.
    :param analyser_qx: Qx object to be used as an analyser for the test suite.
    :param gain: Value to be applied as the gain on the loudness monitor.
    :param loudness_standard: Value for the loudness montitor to use as the standard.
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    fiveone_loudness = fiveone_loudness_settings()
    for _ in range(6):
        fiveone_loudness['channels'][_]['gain_dBFS'] = gain
    # analyser_qx.analyser.loudness_config['audioAssignment'] = channel_assignment()
    generator_qx.generator.audio_custom_config = fiveone_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness logs on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    momentary_peak_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Momentary Peak: '").read().replace('\n', '')
    momentary_peak_value = float(momentary_peak_str.lstrip('Momentary Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(momentary_peak_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(momentary_peak_value, -10.0 - 0.1, -10 + 0.1)


@pytest.mark.parametrize('gain', yield_gain_values(), ids=_generate_gain_formatter)
@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard(), ids=_generate_loudness_standard_formatter)
def test_5_1_short_term(generator_qx: Qx, analyser_qx: Qx, gain: float, loudness_standard: str) -> None:
    """
    Test short term values for 5.1 audio settings in loudness montitoring.

    :param generator_qx: Qx object to be used as a generator for the test suite.
    :param analyser_qx: Qx object to be used as an analyser for the test suite.
    :param gain: Value to be applied as the gain on the loudness monitor.
    :param loudness_standard: Value for the loudness monitor to use as the standard.
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    fiveone_loudness = fiveone_loudness_settings()
    for _ in range(6):
        fiveone_loudness['channels'][_]['gain_dBFS'] = gain
    # analyser_qx.analyser.loudness_config['audioAssignment'] = channel_assignment()
    generator_qx.generator.audio_custom_config = fiveone_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness logs on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    short_term_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Short Term Peak: '").read().replace('\n', '')
    short_term_value = float(short_term_str.lstrip('Short Term Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(short_term_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(short_term_value, -10.0 - 0.1, -10.0 + 0.1)


@pytest.mark.parametrize('gain', yield_gain_values(), ids=_generate_gain_formatter)
@pytest.mark.parametrize('loudness_standard', _generate_loudness_standard(), ids=_generate_loudness_standard_formatter)
def test_5_1_integrated(generator_qx: Qx, analyser_qx: Qx, gain: float, loudness_standard: str) -> None:
    """
    Test integrated values for 5.1 audio settings in loudness monitoring.

    :param generator_qx: Qx object to be used as a generator for the test suite.
    :param analyser_qx: Qx object to be used as an analyser for the test suite.
    :param gain: Value to be applied as the gain on the loudness monitor.
    :param loudness_standard: Value for the loudness monitor to use as the standard.
    """
    tmp_conf = analyser_qx.analyser.loudness_config
    tmp_conf['standard'] = loudness_standard
    analyser_qx.analyser.loudness_config = tmp_conf
    fiveone_loudness = fiveone_loudness_settings()
    for _ in range(6):
        fiveone_loudness['channels'][_]['gain_dBFS'] = gain
    # analyser_qx.analyser.loudness_config['audioAssignment'] = channel_assignment()
    generator_qx.generator.audio_custom_config = fiveone_loudness
    start_stop_loudness(analyser_qx)

    # Retrieve results from loudness logs on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    connect_and_unpack(analyser_qx)
    current_log_text = read_most_recent_log()
    integrated_peak_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Integrated Peak: '").read().replace('\n', '')
    integrated_peak_value = float(integrated_peak_str.lstrip('Integrated Peak: '))
    if loudness_standard == 'ebuLufs':
        assert is_in_range(integrated_peak_value, gain - 0.1, gain + 0.1)
    elif loudness_standard == 'ebuLu' and gain == -33:
        assert is_in_range(integrated_peak_value, -10.0 - 0.1, -10.0 + 0.1)
