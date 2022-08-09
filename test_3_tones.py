"""
Tests to validate the loudness monitoring is accurate over 3 tones of varying duration.
"""
import pytest
import logging
import shutil
import time
import os
from paramiko.client import SSHClient, AutoAddPolicy
from collections.abc import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.analyser import LoudnessReset

# Set up logging for test_system
log = logging.getLogger(test_system_log)


def loudness_modes() -> Generator[str, None, None]:
    """
    Yields the different EBU values for the mode setting for the loudness monitor.

    :return: Generator for the different EBU values for loudness mode.
    """
    yield from ['ebuLu', 'ebuLufs']


def stereo_loudness_settings() -> dict:
    """
    Provides the loudness settings in JSON format.
    """
    return {"channels": [
        {"channel": 0, "frequency_Hz": 1000, "gain_dBFS": 0},
        {"channel": 1, "frequency_Hz": 1000, "gain_dBFS": 0},
    ]}


def channel_assignment() -> dict:
    """
    Provides the JSON used for channel assignment in the tests.
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

    :param host: string
    :return: Qx object to be set for SDI use.
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope="module")
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx generator objectself.

    :param test_generator_hostname: Hostname of the unit to be used as the generator.
    :return: Generator for Qx class for generator_qx
    """
    gen_qx = make_SDI_unit(test_generator_hostname)
    gen_qx.io.set_sdi_outputs(("generator", "generator", "generator", "generator"))
    log.info(f"FIXTURE: Qx {gen_qx.hostname} setup complete.")
    yield gen_qx
    log.info(f"FIXTURE: Qx {gen_qx.hostname} teardown complete.")


@pytest.fixture(scope="module")
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyserself.

    :param test_analyser_hostname: Hostname of the unit to be used as the analyser.
    :return: Generator for the Qx class for analyser_qx
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} setup complete")
    yield analyser_qx
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} teardown complete")


def start_loudness(analyser_qx: Qx) -> None:
    """
    Starts the loudness monitor.

    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    """
    loudness_control = analyser_qx.analyser.loudness_config
    loudness_control["control"] = 'start'
    analyser_qx.analyser.loudness_config = loudness_control


def stop_loudness(analyser_qx: Qx) -> None:
    """
    Stops the loudness monitor.

    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    """
    loudness_control = analyser_qx.analyser.loudness_config
    loudness_control["control"] = 'stop'
    analyser_qx.analyser.loudness_config = loudness_control


def remove_old_logs() -> None:
    """
    Removes the .zip file of a recent loudness test ran by this test.
    """
    os.remove('./loudness_logs.zip')


def remove_extracted_logs() -> None:
    """
    Removes the extracted_logs/ directory after a test has been completed, to avoid
    using outdated values in the next loudness test.
    """
    shutil.rmtree('extracted_logs/')


def connect_and_unpack(analyser_qx: Qx) -> None:
    """
    Connects to a qx/qxl and unpacks the relevant logs to a local destination
    then removes the .zip file associated with the logs.

    :param analyser_qx: Qx object to represent the unit being used as the analyser.
    """
    with SSHClient() as ssh:
        get_loudness_logs(ssh, analyser_qx)
    shutil.unpack_archive('./loudness_logs.zip', 'extracted_logs')
    remove_old_logs()


def get_loudness_logs(ssh: SSHClient, analyser_qx: Qx) -> None:
    """
    Gets the loudness logs from the test unit.

    :param ssh: paramiko.client.SSHClient used to connect to test unit via SSH.
    :param analyser_qx: Qx object used to represent the analyser.
    """
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(analyser_qx.hostname, username='root', password='PragmaticPhantastic')
    sftp = ssh.open_sftp()
    sftp.chdir('/home/sftp/qxuser/transfer/log/loudness/')
    log_list = sftp.listdir()
    log_list.sort()
    latest_log = log_list[-1].strip('\n')
    log_path = f'/home/sftp/qxuser/transfer/log/loudness/{latest_log}'
    sftp.get(log_path, './loudness_logs.zip')


def get_most_recent_log() -> str:
    """
    Return the most recent .txt file from the unzipped logs in extracted_logs dir.

    :return: Path to the most recent .txt file.
    """
    return os.popen("cd extracted_logs/; ls -Art *.txt | tail -n 1").read().replace('\n', '')


def run_3_tones_test(generator_qx: Qx, analyser_qx: Qx) -> None:
    """
    Runs the test, which plays 3 different tones, for 3 different durations

    1st tone and duration is -26.0 for 20 seconds
    2nd tone and duration is -20.0 for 20.1 seconds
    3rd tone and duration is -26.0 for 20 seconds

    :param generator_qx: Qx object to be used as the generator.
    :param analyser_qx: Qx object to be used as the analyser.
    """
    three_tones = [-26.0, -20.0, -26.0]
    three_durations = [20, 20.1, 20]
    stereo_loudness = stereo_loudness_settings()
    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = three_tones[0]
    analyser_qx.analyser.loudness_config = channel_assignment()
    generator_qx.generator.audio_custom_config = stereo_loudness
    start_loudness(analyser_qx)
    time.sleep(three_durations[0])

    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = three_tones[1]
    generator_qx.generator.audio_custom_config = stereo_loudness
    time.sleep(three_durations[1])

    for _ in range(2):
        stereo_loudness['channels'][_]['gain_dBFS'] = three_tones[2]
    generator_qx.generator.audio_custom_config = stereo_loudness
    time.sleep(three_durations[2])
    stop_loudness(analyser_qx)


def get_loudness_value_from_logs(test_unit: Qx) -> float:
    """
    Get the loudness logs from a unit.

    :param test_unit: Qx object used to represent the unit that the logs are being retrieved from.
    :return: Returns the value of the program loudness from the logs.
    """
    connect_and_unpack(test_unit)
    current_log_text = get_most_recent_log()
    program_loudness_str = os.popen(f"cat ./extracted_logs/{current_log_text} | grep 'Program Loudness: '").read().replace('\n', '')
    return float(program_loudness_str.lstrip('Program Loudness: '))


@pytest.mark.parametrize('mode', loudness_modes())
def test_three_tones(generator_qx: Qx, analyser_qx: Qx, mode: str) -> None:
    """
    Set a tone and then check that the tone being recorded by the loudness
    monitor is accurate to what we set it within 0.01 LU.

    :param generator_qx: Qx object used to represent the unit being used as the generator.
    :param analyser_qx: Qx object used to represent the unit being used as the analyser.
    :param mode: The loudness mode to be used.

    Note: As this is an EBU test, only the ebuLu and ebuLufs mode values are valid for this test.
    """
    analyser_qx.analyser.loudness_reset(LoudnessReset.LOUDNESSMONITORING)
    loudness_mode = analyser_qx.analyser.loudness_config
    loudness_mode['standard'] = mode
    analyser_qx.analyser.loudness_config = loudness_mode
    run_3_tones_test(generator_qx, analyser_qx)

    # Retrieve results from loudness log on the qx unit in
    # /home/sftp/qxuser/transfer/log/loudness

    program_loudness_value = get_loudness_value_from_logs(analyser_qx)
    print(f'{mode} mode. Value {program_loudness_value}')
    if mode == 'ebuLufs':
        assert program_loudness_value in {-22.9, -23.0, -23.1}
    else:
        assert program_loudness_value in {-0.1, 0.0, 0.1}

    os.system('rm ./extracted_logs/ -rf')
