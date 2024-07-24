"""\
Tests to confirm that the SDI Analyser methods behave as expected against a real Qx.

These tests require a Qx type device to be available so should not be run by CI. As such
a marker has been applied to indicate this.
"""

import os
import time
import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.models.qxseries.prbs import PRBSResponse
from autolib.models.qxseries.analyser import CableType, AudioData, AudioMeter

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
class TestSDIAnalyser:
    def test_sdi_about(self, sdi_qx):
        about_details = sdi_qx.about
        assert isinstance(about_details, dict)

        # Install a specific version and then remove keys() superset comparison
        assert about_details.keys() >= {'Build_number': '746674551',
                                        'FPGA_version': '4.8.0+64635',
                                        'IP': '192.168.0.190',
                                        'Image_version': 'release_v4_3_6',
                                        'Software_version': '4.8.0',
                                        'device': 'QxL',
                                        'firmware_mode': 'QxL Master',
                                        'hostname': 'qx-022005.phabrix.local',
                                        'main_pcb_rev': '66',
                                        'mezzanine_rev': '12',
                                        'sha': 'f343827dcf8ea9a54282bcb5231972f275aecc1e',
                                        'software_branch': 'demo/v4_8_0_with_nmos_traffic_capture'}.keys()

    def test_common_analyser(self, sdi_qx):
        """\
        Test the methods in the Analyser class itself that are shared between modes
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        # time.sleep(5)
        # assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")

        # assert sdi_qx.analyser.max_audio_groups == 4
        #
        # assert sdi_qx.analyser.get_audio(AudioData.LEVEL) == []
        # assert sdi_qx.analyser.get_audio(AudioData.PHASE) == []
        # assert AudioMeter.from_value(sdi_qx.analyser.get_audio(AudioData.BALLISTICS)) == AudioMeter.PPM_TYPE_I

    def test_sdi_standard_analyser(self, sdi_qx):
        """\
        Test the SDI analyser methods.
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")

        assert sdi_qx.analyser.sdi.get_analyser_status() == ('1920x1080i59.94', 'YCbCr:422:10', '1.5G_Rec.709')

        assert sdi_qx.analyser.sdi.get_analyser_datarate() == 1.5
        assert sdi_qx.analyser.sdi.get_analyser_datarate() not in [3.0, 6.0, 12.0]

        assert sdi_qx.analyser.sdi.expected_video_analyser("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709") is True
        assert sdi_qx.analyser.sdi.expected_video_analyser("1920x1080i59.94", "YCbCr:422:12", "1.5G_Rec.709") is False
        assert sdi_qx.analyser.sdi.expected_video_analyser("1920x1080p59.94", "YCbCr:422:10", "1.5G_Rec.709") is False
        assert sdi_qx.analyser.sdi.expected_video_analyser("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.2020") is False

        assert sdi_qx.analyser.sdi.verify_clock_divisor()

    def test_sdi_crc_analyser(self, sdi_qx):
        """\
        Test the SDI CRC analyser methods.
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709",
                                                       "100% Bars")

        assert sdi_qx.analyser.sdi.crc_summary.keys() >= {'activePictureCrcChanges': 0,
                                                          'errorCount': 0,
                                                          'ignoreCrcOnSwitchLines': 'disabled',
                                                          'inputFailures': 6,
                                                          'okTime_ms': 434981,
                                                          'rate_/s': 0,
                                                          'timeSinceInputFailure': 434981}.keys()

        crc_data = sdi_qx.analyser.sdi.get_crc_analyser()
        assert len(crc_data) == 1
        assert crc_data[0].keys() >= {'activePictureCrc': 'cc776e94',
                                      'activePictureCrcChanges': 0,
                                      'ancErrorCountCPos': 0,
                                      'ancErrorCountYPos': 0,
                                      'errorCountCPos': 0,
                                      'errorCountYPos': 0,
                                      'okTime_ms': 1040686,
                                      'rate_/s': 0}.keys()
        assert crc_data[0].get('activePictureCrc', '') == 'cc776e94'

        sdi_qx.analyser.sdi.reset_crc()
        assert isinstance(sdi_qx.analyser.sdi.get_crc_last_input_failure(), int)

        assert sdi_qx.analyser.sdi.validate_crc()

        # Need to set up to check the CRC analyser reports when there are problems
        # Here.
        # assert sdi_qx.analyser.sdi.validate_crc()

    def test_sdi_dataview_analyser(self, sdi_qx):
        """\
        Test the SDI dataview analyser methods.
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709",
                                                       "100% Bars")

        assert sdi_qx.analyser.sdi.cursors_active_picture_cursor.keys() >= {'activePictureLine': 1,
                                                                            'activePicturePixel': 0,
                                                                            'sourcePositionLine': 21,
                                                                            'sourcePositionPixel': 0}.keys()

        sdi_qx.analyser.sdi.move_active_picture_cursor(10, 10)
        assert sdi_qx.analyser.sdi.get_analyser_dataview() == {'Cb': 512, 'Cr': 512, 'Y': 940}

    def test_sdi_prbs_analyser(self, sdi_qx):
        """\
        Test the SDI prbs analyser methods.
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709",
                                                       "100% Bars")

        assert sdi_qx.analyser.sdi.prbs.keys() >= {'analyserTime': '13m 30s',
                                                   'receiveMode': 'Disabled'}.keys()

        # Not sure there's much point to this method
        assert isinstance(sdi_qx.analyser.sdi.get_prbs(), PRBSResponse)

    def test_sdi_cable_type_analyser(self, sdi_qx):
        """\
        Test the SDI cable type analyser methods.
        """
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        assert sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709",
                                                       "100% Bars")

        sdi_qx.analyser.sdi.set_cable_type(CableType.BELDEN_1694A)
        assert sdi_qx.analyser.sdi.cable_length.items() >= {'attenuationA': 0,
                                                            'attenuationB': 0,
                                                            'attenuationC': 0,
                                                            'attenuationD': 0,
                                                            'cableType': 'belden_1694a',
                                                            'lengthA': 0,
                                                            'lengthB': 0,
                                                            'lengthC': 0,
                                                            'lengthD': 0}.items()

        for cable_type in CableType:
            sdi_qx.analyser.sdi.set_cable_type(cable_type)
            assert sdi_qx.analyser.sdi.cable_length.get('cableType', '') == cable_type.value
