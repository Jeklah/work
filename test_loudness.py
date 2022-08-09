"""\
Tests to validate the basic functionality of setting loudness config and controls.
"""
import pytest
import logging
import numpy as np
from time import sleep
from typing import Generator
from test_system.factory import make_qx, Qx
from test_system.logconfig import test_system_log
from test_system.models.qxseries.io import SDIIOType
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.analyser import AnalyserException


# Set up logging for test_system
log = logging.getLogger(test_system_log)


def make_SDI_unit(host: str) -> Qx:
    """
    Abstraction function for creating Qx objects that support SDI,
    depending on licences.

    :param host: Hostname of the unit under test.
    :return: Qx
    """
    qx = make_qx(hostname=host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates Qx generator object using test_generator_hostname env var.

    :param test_generator_hostname: Hostname of the unit to be used as Generator
    :return: Qx object to be used as the Generator
    """
    gen_qx = make_SDI_unit(test_generator_hostname)
    gen_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'FIXTURE: Qx {gen_qx.hostname} setup complete')
    yield gen_qx
    log.info(f'FIXTURE: Qx {gen_qx.hostname} teardown complete')


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Creates a Qx object and configures it to be used as the analyser.

    :param test_analyser_hostname: string
    :return: object
    """
    analyser_qx = make_SDI_unit(test_analyser_hostname)
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} setup complete')
    yield analyser_qx
    log.info(f'FIXTURE: Qx {analyser_qx.hostname} teardown complete')


def generate_loudness_log_duration() -> Generator[int, None, None]:
    """
    Yields valid values for loudness log duration.

    :yield: int
    """
    yield from [5, 15, 30, 60, 120, 180, 360, 720, 1440]


def generate_loudness_log_lifetime() -> Generator[int, None, None]:
    """
    Yields valid values for loudness log lifetime.

    :yield: int
    """
    yield from [1, 7, 14, 30]


def generate_loudness_meter_target() -> Generator[dict, None, None]:
    """
    Yields valid values for momentary, shortTerm and integrated fields.

    :yield: dict
    """
    for num in range(-60, -4):
        yield dict(integrated=num, momentary=num, shortTerm=num)


def generate_loudness_meter_tolerance() -> Generator[dict, None, None]:
    """
    Yields valid values for meter tolerance.

    :yield: dict
    """
    for num in np.arange(0, 10, 0.1):
        num = round(num, 1)
        yield dict(integrated=num, momentary=num, shortTerm=num)


def generate_loudness_unit() -> Generator[str, None, None]:
    """
    Yields valid values for measuring loudness in.

    :yield: str
    """
    yield from ['ebuLufs', 'ebuLu', 'ituLkfs', 'ituLu']


def _generate_loudness_control() -> Generator[str, None, None]:
    """Yields valid values for loudness control."""
    yield from ['play', 'stop', 'pause']


@pytest.mark.parametrize('control', _generate_loudness_control())
def test_loudness_control(analyser_qx: Qx, control: str):
    """
    Tests whether the start, stop and pause controls work as intended.

    :param analyser_qx: Qx object to be used as the analyser.
    """
    try:
        current_control_config = analyser_qx.analyser.loudness_config
        if current_control_config['status'] == 200:
            new_config = current_control_config
            if control and current_control_config['control'] == 'stop':
                new_config['control'] = 'start'
            elif control and current_control_config['control'] == 'start':
                new_config['control'] = 'pause'
            else:
                new_config['control'] = 'stop'
            analyser_qx.analyser.loudness_config = new_config
            assert analyser_qx.analyser.loudness_config['control'] == new_config['control']
        else:
            log.error(f"{analyser_qx.hostname}: An error occurred while getting the loudness configuration. {current_control_config['status']}")
    except AnalyserException as loudness_exc:
        log.error(f'{analyser_qx.hostname}: An unexpected error occurred. {loudness_exc}')


def _generator_log_duration_formatter(args: int) -> str:
    """
    Format test IDs for loudness log duration test.
    """
    log_dur = args
    return f'Log Duration: {log_dur}'


@pytest.mark.parametrize('log_duration', generate_loudness_log_duration(), ids=_generator_log_duration_formatter)
def test_loudness_log_duration(analyser_qx: Qx, log_duration: int) -> None:
    """
    Tests that the duration of the loudness logs are set correctly, duration in minutes.

    :param analyser_qx: Qx object to be used as the analyser.
    :param log_duration: Duration for the log to be in minutes.
    """
    try:
        current_log_dur_config = analyser_qx.analyser.loudness_config
        if current_log_dur_config['status'] == 200:
            new_config = current_log_dur_config
            new_config['logDuration_mins'] = log_duration
            analyser_qx.analyser.loudness_config = new_config
            assert analyser_qx.analyser.loudness_config['logDuration_mins'] == log_duration
        else:
            log.error(f"{analyser_qx.hostname}: An error occurred while getting the loudness configuration. {current_log_dur_config['status']}")
    except AnalyserException as loudness_exc:
        log.error(f'{analyser_qx.hostname}: An unexpected error occurred. {loudness_exc}')


def _generator_log_lifetime_formatter(args: str) -> str:
    """
    Format test IDs for loudness log lifetime test.

    :param args: String containing arguments to be passed to the formatter.
    :return: Log lifetime value.
    """
    log_life = args
    return f'Log Lifetime: {log_life}'


@pytest.mark.parametrize('log_lifetime', generate_loudness_log_lifetime(), ids=_generator_log_lifetime_formatter)
def test_loudness_log_lifetime(analyser_qx: Qx, log_lifetime: int) -> None:
    """
    Tests that the lifetime of the loudness logs are set correctly, lifetime in days.

    :param analyser_qx: Qx object to be used as the analyser.
    :param log_lifetime: Duration for the log to be in days.
    """
    try:
        new_config = analyser_qx.analyser.loudness_config
        new_config['logLifetime_days'] = log_lifetime
        analyser_qx.analyser.loudness_config = new_config
        assert analyser_qx.analyser.loudness_config['logLifetime_days'] == log_lifetime
    except AnalyserException as log_life_err:
        log.error(f'{analyser_qx.hostname}: An unexpected error occurred. {log_life_err}.')


def _generator_meter_target_formatter(args: dict) -> str:
    """
    Format test IDs for the loudness meter target test.
    :param args: Dictionary containing the values for the different values of loudness that can be displayed.
    :return: String containing the value of the Meter Target.
    """
    integrated = args['integrated']
    momentary = args['momentary']
    shortTerm = args['shortTerm']
    meter_target = f'Integrated: {integrated} Momentary: {momentary} ShortTerm: {shortTerm}'
    return f'Meter Target: {meter_target}'


@pytest.mark.parametrize('meter_target', generate_loudness_meter_target(), ids=_generator_meter_target_formatter)
def test_loudness_meter_target(analyser_qx: Qx, meter_target: dict) -> None:
    """
    Tests that the different targets for the loudness meter are set within correct range.  # need to add sad tests for this and similar.

    :param analyser_qx: Qx object to be used as the analyser.
    :param meter_target: Dictionary containing values for the meter target.
    """
    try:
        current_meter_target_config = analyser_qx.analyser.loudness_config
        if current_meter_target_config['status'] == 200:
            new_config = current_meter_target_config
            new_config['meterTarget'] = meter_target
            analyser_qx.analyser.loudness_config = new_config
            assert analyser_qx.analyser.loudness_config['meterTarget'] == meter_target
        else:
            log.error(f"{analyser_qx.hostname}: An error occurred while getting the loudness configuration. {current_meter_target_config['status']}")
    except AnalyserException as loudness_exc:
        log.error(f"{analyser_qx.hostname}: An unexpected error occurred. {loudness_exc}")


def _generator_meter_tolerance_formatter(args: dict) -> str:
    """
    Format test IDs for the loudness meter tolerance test.
    """
    integrated = args['integrated']
    momentary = args['momentary']
    shortTerm = args['shortTerm']
    meter_tolerance = f'Integrated: {integrated} Momentary: {momentary} ShortTerm: {shortTerm}'
    return f'Meter Tolerance: {meter_tolerance}'


@pytest.mark.parametrize('meter_tolerance', generate_loudness_meter_tolerance(), ids=_generator_meter_tolerance_formatter)
def test_loudness_meter_tolerance(analyser_qx: Qx, meter_tolerance: dict) -> None:
    """
    Tests that the meter tolerance is set within correct range.

    :param analyser_qx: Qx object to be used as the analyser.
    :param meter_tolerance: Dictionary containing values for the meter tolerance.
    """
    try:
        current_meter_tolerance_config = analyser_qx.analyser.loudness_config
        if current_meter_tolerance_config['status'] == 200:
            new_config = current_meter_tolerance_config
            new_config['meterTolerance'] = meter_tolerance
            analyser_qx.analyser.loudness_config = new_config

            # When this test is run without a brief pause in between setting the configuration and checking
            # it is what it should be, it appears that the non rounded version somehow makes it into
            # the configuration. With the 0.75 sleep, it is correctly rounded.

            sleep(0.75)
            assert analyser_qx.analyser.loudness_config['meterTolerance'] == meter_tolerance
        else:
            log.error(f"{analyser_qx.hostname}: An error occurred while getting the loudness configuration. {current_meter_tolerance_config['status']}.")
    except AnalyserException as loudness_exc:
        log.error(f'{analyser_qx.hostname}: An unexpected error occurred. {loudness_exc}.')


def _generate_standard_unit_formatter(args: tuple) -> str:
    """
    Format test IDs for loudness standard unit test.
    """
    std_unit = args
    return f'Standard Unit: {std_unit}'


@pytest.mark.parametrize('loudness_unit', generate_loudness_unit(), ids=_generate_standard_unit_formatter)
def test_loudness_standard_unit(analyser_qx: Qx, loudness_unit: str) -> None:
    """
    Tests that the 'standard' field in the loudness configuration is set correctly.

    :param analyser_qx: Qx object to be used as the analyser.
    :param loudness_unit: Unit for loudness to be measured in.
    """
    try:
        current_standard_unit_config = analyser_qx.analyser.loudness_config
        if current_standard_unit_config['status'] == 200:
            new_config = current_standard_unit_config
            new_config['standard'] = loudness_unit
            analyser_qx.analyser.loudness_config = new_config

            assert analyser_qx.analyser.loudness_config['standard'] == loudness_unit
        else:
            log.error(f"{analyser_qx.hostname}: An error occurred while getting the loudness configuration. {current_standard_unit_config['status']}.")
    except AnalyserException as loudness_exc:
        log.error(f'{analyser_qx.hostname}: An unexpected error occurred. {loudness_exc}.')
