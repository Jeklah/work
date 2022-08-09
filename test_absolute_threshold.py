"""\
Tests to validate the absolute threshold is triggered correctly.
"""
import pytest
import logging
import numpy as np
import time
from collections.abc import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def make_SDI_unit(host: str) -> Qx:
    """
    Function for creating Qx objects that support SDI.

    :param host: string
    :return: object
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx generator objectself.

    :param test_generator_hostname: Hostname of a Qx to be used as the generator.
    :return: Generator for Qx objects to be used in this test.
    """
    gen_qx = make_SDI_unit(host=test_generator_hostname)
    gen_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'FIXTURE: Qx {gen_qx.hostname} setup complete.')
    yield gen_qx
    log.info(f'FIXTURE: Qx {gen_qx.hostname} teardown complete.')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyserself.

    :param test_analyser_hostname: Hostname of the unit to be used as the analyser for this test.
    :return:  Generator for Qx objects to be used in this test.
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete')
    yield analyser_qx
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete')


@pytest.fixture(scope='module')
def test_absolute_threshold(generator_qx: Qx, analyser_qx: Qx, loudness_channel_config: dict) -> None:
    """
    Checks the absolute threshold is triggered correctly.
    """
    # set up tones, channels and gaindBFS
    loudness_abs_settings_20db = {'channels': [
        {'channel': 0, 'frequency_Hz': 261, 'gain_dBFS': -20},
        {'channel': 1, 'frequency_Hz': 261, 'gain_dBFS': -20},
        {'channel': 2, 'frequency_Hz': 261, 'gain_dBFS': -20},
        {'channel': 3, 'frequency_Hz': 261, 'gain_dBFS': -20},
    ]}
    loudness_abs_settings_30db = {'channels': [
        {'channel': 0, 'frequency_Hz': 261, 'gain_dBFS': -30},
        {'channel': 1, 'frequency_Hz': 261, 'gain_dBFS': -30},
        {'channel': 2, 'frequency_Hz': 261, 'gain_dBFS': -30},
        {'channel': 3, 'frequency_Hz': 261, 'gain_dBFS': -30},
    ]}
    duration=20
    loudness_config=generator_qx.generator.audio['customConfig']['channels']
    generator_qx.analyser.loudness_config['control']='start'
    start=time.perf_counter()
    time.sleep(20)
    stop=time.perf_counter()
    generator_qx.analyser.loudness_config['control']='stop'

### this is a work in progress.








