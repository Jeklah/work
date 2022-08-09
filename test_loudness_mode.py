"""\
Test to validate the audio mode for loudness monitoring is set correctly.
"""
import time
import pytest
import logging
from typing import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def make_SDI_unit(host: str) -> Qx:
    """
    Abstraction function for creating Qx object that supports SDI,
    depending on licences.

    :param host: string
    :return: qx object
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates Qx generator object using test_generator_hostname env var.

    :param test_generator_hostname: string
    :return: Generator object to be used with Qx object for generators.
    """
    generator_qx = make_SDI_unit(test_generator_hostname)
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'FIXTURE: Qx {generator_qx.hostname} setup complete')
    yield generator_qx
    log.info(f'FIXTURE: Qx {generator_qx.hostname} teardown complete.')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyser.

    :param test_analyser_hostname: string
    :return: Generator object to be used with Qx object for analysers.
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete')
    yield analyser_qx
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete')


def generate_audio_mode() -> Generator[str, None, None]:
    """
    Yields possible valid values for audio assignment for us to enumerate though.

    :yield: string
    """
    yield from ['stereo', '5.1']
    # 'aesStereo'


def _generator_audio_mode_formatter(args: str) -> str:
    """
    Format test IDs for test_audio_mode

    :param: Arguments to be fed into test_audio_mode.
    """
    audio_mode = args
    return f'Audio Mode: {audio_mode}'


@pytest.mark.parametrize('audio_mode_val', generate_audio_mode(), ids=_generator_audio_mode_formatter)
def test_audio_mode(analyser_qx: Qx, audio_mode_val: str) -> None:
    """
    Set the audio mode to a valid setting and then check it is what we expect
    it to be.

    :param analyser_qx: object
    :param audio_mode_val: str
    """
    curr_config = analyser_qx.analyser.loudness_config
    expected_result = audio_mode_val
    new_config = curr_config
    new_config['audioAssignment']['audioMode'] = audio_mode_val
    analyser_qx.analyser.loudness_config = new_config
    time.sleep(0.5)
    assert analyser_qx.analyser.loudness_config['audioAssignment']['audioMode'] == expected_result
