"""
Tests in this module perform fundamental tests against the presets Rest API
"""

import logging
import os

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.qx import TemporaryPreset
from autolib.logconfig import autolib_log

log = logging.getLogger(autolib_log)


@pytest.fixture
def test_qx(test_qx_hostname):
    """
    Pytest fixture that will create a Qx object using the test_qx_hostname global fixture.
    """
    qx = make_qx(test_qx_hostname)
    log.info(f"FIXTURE: Qx {qx.hostname} setup complete")
    yield qx
    log.info(f"FIXTURE: Qx {qx.hostname} teardown complete")


@pytest.mark.fundamental
@pytest.mark.smoke
@pytest.mark.parametrize("op_mode,preset_suffix", (
        (OperationMode.SDI, "_sdi_smoke_test.json"),
        (OperationMode.IP_2022_6, "_ip_2022_6_smoke_test.json"),
        (OperationMode.IP_2110, "_ip_2110_smoke_test.json")
    ), ids=('SDI', '2022-6', '2110'))
def test_preset_upload_and_use(op_mode, preset_suffix, test_qx):
    """
    Place the test device in each operation mode and run a set of fundamental preset tests.
    """
    module_path = os.path.dirname(os.path.realpath(__file__)).rstrip(os.path.sep)

    log.info(f"Starting {op_mode} presets test on {test_qx.hostname} - requesting capability: {op_mode}")
    test_qx.request_capability(op_mode)

    preset_file = f"{module_path}{os.path.sep}_{type(test_qx).__name__}{preset_suffix}"

    # A basic test using the Temporary Preset context manager to upload, activate, check for and then delete
    # which we'll do 10 times in a row.
    for index in range(10):
        log.info(f"Uploading a preset {preset_file} as smoke_test_init on {test_qx.hostname} - test index: {index}")
        preset_name = f'preset_test_{op_mode.name}'
        with TemporaryPreset(test_qx, preset_file, f'preset_test_{op_mode.name}'):
            assert(preset_name in test_qx.preset.list())
