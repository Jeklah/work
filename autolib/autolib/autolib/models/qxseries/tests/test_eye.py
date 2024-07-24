"""\
Tests to confirm that the SDI Eye methods behave as expected against a real Qx.

These tests require a Qx type device to be available so should not be run by CI. As such
a marker has been applied to indicate this.
"""

import os
import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode

TEST_UNIT = os.environ.get('TS48_TEST_UNIT', 'qx-020008.phabrix.local')


@pytest.fixture(scope="class")
def sdi_qx():
    """\
    Return a Qx series device in SDI mode with default settings.
    """
    qx = make_qx(TEST_UNIT)
    # Install a set version and change the about test to check the precise content.
    qx.restore_initial_state()
    qx.request_capability(OperationMode.SDI)
    yield qx


@pytest.mark.requires_device
class TestSDIEye:
    def test_eye_dc_offset(self, sdi_qx):
        dc_offset = sdi_qx.eye.get_eye_dc_offset()
        assert isinstance(dc_offset, tuple)
        assert len(dc_offset) == 3
        for item in dc_offset:
            assert isinstance(item, float)

    def test_eye_histogram_width(self, sdi_qx):
        dc_offset = sdi_qx.eye.get_eye_histogram_width()
        assert isinstance(dc_offset, int)

    def test_eye_rise_fall_times(self, sdi_qx):
        rise_fall = sdi_qx.eye.get_eye_rise_fall_times()
        assert isinstance(rise_fall, tuple)
        assert len(rise_fall) == 3
        for item in rise_fall:
            assert isinstance(item, (float, int))

    def test_eye_status(self, sdi_qx):
        assert sdi_qx.eye.eye_status.keys() >= {
            "dcOffset_mV": 0,
            "fallTime_ps": 56.08333969116211,
            "inputIsStable": True,
            "maxVoltage_mV": 399.762451171875,
            "minVoltage_mV": -399.762451171875,
            "negativeOvershoot_percent": 2.9000000953674316,
            "positiveOvershoot_percent": 2.6000001430511475,
            "riseTime_ps": 56.08332824707031}.keys()

    def test_eye_analysis_parameters(self, sdi_qx):
        assert sdi_qx.eye.eye_analysis_parameters.keys() >= {
            'amplitudeMeasurementWindowOffset_percent': 0,
            'amplitudeMeasurementWindowSize_percent': 100,
            'analysisMethod': 'mode'
        }.keys()

    def test_devtools_eye_histogram(self, sdi_qx):
        assert sdi_qx.eye.devtools_eye_histogram.keys() >= {
            'eyeHistogramWidth': '7'
        }.keys()

    def test_eye_jitter_comp_filter(self, sdi_qx):
        sdi_qx.eye.set_jitter_comp_filter(True)
        # How to confirm?

    def test_eye_jitter_filter(self, sdi_qx):
        for frequency in [10, 100, 1000, 10000, 10000]:
            sdi_qx.eye.set_jitter_filter(frequency)
            # How to confirm?
