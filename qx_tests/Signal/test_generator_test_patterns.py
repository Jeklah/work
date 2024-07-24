"""
A suite of tests to exercise the generator and the generator REST API.
"""

import logging
import os
import time

import pytest

from autolib.retry import retry, retry_ignoring_exceptions
from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.qx import TemporaryPreset
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode


log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates generator qx object using test_generator_hostname global. All tests in this
    suite are SDI tests and require the bouncing box and output copy to be disabled.
    """
    generator_qx = make_qx(test_generator_hostname)
    module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)
    preset_file = f"{module_path}{os.path.sep}{type(generator_qx).__name__}_sdi_all_windows.json"
    default_preset_name = f"{module_path}{os.path.sep}{type(generator_qx).__name__}_sdi_default_settings.json"

    with TemporaryPreset(generator_qx, preset_file, "AllWindowsOpen"):
        generator_qx.request_capability(OperationMode.SDI_STRESS)
        generator_qx.generator.bouncing_box = False
        generator_qx.generator.output_copy = False
        generator_qx.generator.jitter_insertion("Disabled", 0.01, 10)
        generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
        log.info(f"FIXTURE: Qx {generator_qx.hostname} setup complete")
        yield generator_qx
        generator_qx.generator.bouncing_box = False
        log.info(f"FIXTURE: Qx {generator_qx.hostname} teardown complete")

    with TemporaryPreset(generator_qx, default_preset_name, "Defaults"):
        pass    # Upload the default preset, activate it and then delete it


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    """
    Creates analyser qx object using test_analyser_hostname global.
    """
    analyser_qx = make_qx(test_analyser_hostname)
    analyser_qx.request_capability(OperationMode.SDI_STRESS)
    analyser_qx.io.sdi_input_source = SDIIOType.BNC
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} setup complete")
    yield analyser_qx
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} teardown complete")


@pytest.mark.sdi_stress
@pytest.mark.timeout(120, method='thread')
@pytest.mark.parametrize('res,colour_map,gamut', (
        ("1920x1080p25", "YCbCr:422:10", "1.5G_Rec.709"),
        ("1920x1080p50", "YCbCr:422:10", "3G_A_Rec.709"),
        ("1920x1080i50", "YCbCr:422:10", "1.5G_Rec.709"),
        ("1920x1080p60", "YCbCr:422:10", "3G_A_Rec.2020")
    ))
def test_generator_test_pattern_then_get(generator_qx, analyser_qx, res, colour_map, gamut):
    """
    Generate a given standards for each of it's supported test patterns immediately checking the
    generator status to ensure that it lists the correct test pattern.

    This test originates from a Customer issue raised that when manipulating the standard via the
    REST API, the reported test pattern sometimes went out of sync with the actual live generator
    configuration. Please see Defect 3403.

    * Generate a standard given standard
    * Confirm that the generator thinks it's generating the right test pattern
    """
    valid_patterns = generator_qx.generator.get_test_patterns(res, colour_map, gamut)
    for test_pattern in valid_patterns:
        generator_qx.generator.set_generator(res, colour_map, gamut, test_pattern)
        assert generator_qx.generator.generator_status.get('pattern', None) == test_pattern


@pytest.mark.sdi_stress
@pytest.mark.timeout(120, method='thread')
@pytest.mark.parametrize('res,colour_map,gamut,test_pattern,crcs', (
        ("1920x1080p25", "YCbCr:422:10", "1.5G_Rec.709", "75% Bars", ('5fc581a9', )),
        ("1920x1080i50", "YCbCr:422:10", "1.5G_Rec.709", "75% Bars", ('5fc581a9', )),
        ("1920x1080p60", "YCbCr:422:10", "3G_A_Rec.2020", "75% Bars", ('6ba2cee6', )),
        ("1920x1080p50", "YCbCr:422:10", "3G_A_Rec.709", "75% Bars", ('5fc581a9', )),
    ))
def test_generator_test_pattern(generator_qx, analyser_qx, res, colour_map, gamut, test_pattern, crcs):
    """
    Generate various standards using the non-default test pattern and check that the REST API responses
    confirm that the correct test patterns are being generated (double checking with the frame CRC).

    * Disable the bouncing box
    * Generate a standard given standard
    * Allow 5s for the analyser to settle
    * Confirm that the generator thinks it's generating the right standard and test pattern
    * Confirm that the analyser thinks it's receiving the correct standard
    * Check the test pattern in the generator status
    * Get the frame CRCs from the analyser and compare to expected CRCs
    """
    generator_qx.generator.set_generator(res, colour_map, gamut, test_pattern)

    success, _, exc = retry(10, 1, generator_qx.generator.is_generating_standard, res, colour_map, gamut, test_pattern)
    if not success:
        pytest.fail(f"Generator didn't report generation of the standard and pattern. Exceptions thrown: {exc}")

    success, _, exc = retry_ignoring_exceptions(10, 1, analyser_qx.analyser.sdi.expected_video_analyser, res, colour_map,
                                                gamut)
    if not success:
        pytest.fail(f"Analyser didn't report analysis of the standard and pattern. Exceptions thrown: {exc}")

    assert generator_qx.generator.generator_status.get('pattern', None) == test_pattern

    for _ in range(10):
        crc_response = generator_qx.analyser.sdi.get_crc_analyser()
        if crc_response[0].get('activePictureCrc', None) != "0":
            break
        time.sleep(1)
    else:
        pytest.fail("Failed to read frame CRCs")

    pict_crcs = [x.get('activePictureCrc', None) for x in crc_response]
    assert len(crcs) == len(pict_crcs)

    for expected_crc, recorded_crc in zip(crcs, pict_crcs):
        assert expected_crc == recorded_crc


def switching_pattern_formatter(args):
    res, colour_map, gamut, test_pattern_and_crcs = args
    return f'{res}-{colour_map}-{gamut}-{test_pattern_and_crcs[0][0]}-{test_pattern_and_crcs[1][0]}'


@pytest.mark.sdi_stress
@pytest.mark.timeout(120, method='thread')
@pytest.mark.parametrize('res,colour_map,gamut,test_pattern_and_crcs', (
    (
        "1920x1080p25", "YCbCr:422:10", "1.5G_Rec.709",
        (
            ("100% Bars", ('cc776e94', )),
            ("75% Bars", ('5fc581a9', ))
        )
    ),
    (
        "1920x1080i50", "YCbCr:422:10", "1.5G_Rec.709",
        (
            ("100% Bars", ('cc776e94', )),
            ("75% Bars", ('5fc581a9', ))
        )
    ),
    (
        "1920x1080p60", "YCbCr:422:10", "3G_A_Rec.2020",
        (
            ("100% Bars", ('60e2a6e4', )),
            ("75% Bars", ('6ba2cee6', )),
            ("Circle", ('bfacd6b0', )),
            ("Legal Ramp", ('11f5897f', )),
        )
    ),
    (
        "1920x1080p50", "YCbCr:422:10", "3G_A_Rec.709",
        (
            ("100% Bars", ('cc776e94', )),
            ("75% Bars", ('5fc581a9', ))
        )
    )
))
def test_switching_generator_test_pattern(generator_qx, analyser_qx, res, colour_map, gamut, test_pattern_and_crcs):
    """
    Generate various standards using the non-default test pattern and check that the REST API responses
    confirm that the correct test patterns are being generated (double checking with the frame CRC).

    * Disable the bouncing box
    * Generate a standard given standard
    * Allow 5s for the analyser to settle
    * Confirm that the generator thinks it's generating the right standard and test pattern
    * Confirm that the analyser thinks it's receiving the correct standard
    * Check the test pattern in the generator status
    * Get the frame CRCs from the analyser and compare to expected CRCs
    """
    for test_pattern, crcs in test_pattern_and_crcs:
        generator_qx.generator.set_generator(res, colour_map, gamut, test_pattern)

        success, _, exc = retry(10, 1, generator_qx.generator.is_generating_standard, res, colour_map, gamut,
                                test_pattern)
        if not success:
            pytest.fail(f"Generator didn't report generation of the standard and pattern. Exceptions thrown: {exc}")

        success, _, exc = retry_ignoring_exceptions(10, 1, analyser_qx.analyser.sdi.expected_video_analyser, res,
                                                    colour_map, gamut)
        if not success:
            pytest.fail(f"Analyser didn't report analysis of the standard and pattern. Exceptions thrown: {exc}")

        assert generator_qx.generator.generator_status.get('pattern', None) == test_pattern

        for _ in range(10):
            crc_response = generator_qx.analyser.sdi.get_crc_analyser()
            if crc_response[0].get('activePictureCrc', None) != "0":
                break
            time.sleep(1)
        else:
            pytest.fail("Failed to read frame CRCs")

        pict_crcs = [x.get('activePictureCrc', None) for x in crc_response]
        assert len(crcs) == len(pict_crcs)

        for expected_crc, recorded_crc in zip(crcs, pict_crcs):
            assert expected_crc == recorded_crc
