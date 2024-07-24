"""\
Tests to confirm that the SDI Generator methods behave as expected against a real Qx.

These tests require a Qx type device to be available so should not be run by CI. As such
a marker has been applied to indicate this.
"""

import os
import pytest
import time

from autolib.factory import make_qx
from autolib.models.qxseries.operationmode import OperationMode
from autolib.coreexception import CoreException

BASIC_STANDARD_CRC: str = 'cc776e94'

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
class TestSDIGenerator:
    """\
    Test the SDI Generator methods.
    """

    def _generate_basic_standard(self, sdi_qx):
        sdi_qx.generator.set_generator("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        time.sleep(5)
        is_generating = sdi_qx.generator.is_generating_standard("1920x1080i59.94", "YCbCr:422:10", "1.5G_Rec.709", "100% Bars")
        analyser_happy = sdi_qx.analyser.sdi.get_analyser_status() == ('1920x1080i59.94', 'YCbCr:422:10', '1.5G_Rec.709')
        return is_generating and analyser_happy

    def test_generator_bouncing_box(self, sdi_qx):
        """\
        Test Generator bouncing box
        """
        assert self._generate_basic_standard(sdi_qx)

        sdi_qx.generator.bouncing_box = False
        assert sdi_qx.generator.bouncing_box is False
        time.sleep(1)
        assert sdi_qx.analyser.sdi.get_crc_analyser()[0].get('activePictureCrc', '') == BASIC_STANDARD_CRC

        sdi_qx.generator.bouncing_box = True
        assert sdi_qx.generator.bouncing_box is True
        time.sleep(1)
        assert sdi_qx.analyser.sdi.get_crc_analyser()[0].get('activePictureCrc', '') != BASIC_STANDARD_CRC

        sdi_qx.generator.bouncing_box = False
        assert sdi_qx.generator.bouncing_box is False

    def test_generator_output_copy(self, sdi_qx):
        """\
        Test Generator output copy.
        """
        self._generate_basic_standard(sdi_qx)

        sdi_qx.generator.output_copy = True
        assert sdi_qx.generator.output_copy is True

        sdi_qx.generator.output_copy = False
        assert sdi_qx.generator.output_copy is False

    def test_generator_output_mutes(self, sdi_qx):
        """\
        Test Generator output mutes
        """
        self._generate_basic_standard(sdi_qx)

        sdi_qx.generator.mute_sdi_outputs((True, True, True, True))
        time.sleep(1)

        with pytest.raises(CoreException):
            sdi_qx.analyser.sdi.get_crc_analyser()[0].get('activePictureCrc', '')

        sdi_qx.generator.mute_sdi_outputs((False, False, False, False))
        time.sleep(1)

        assert sdi_qx.analyser.sdi.get_crc_analyser()[0].get('activePictureCrc', '') == BASIC_STANDARD_CRC

    @pytest.mark.skip("This doesn't seem to work - is there actually a problem with the REST API?")
    def test_audio_generator_group_config(self, sdi_qx):
        """\
        Test audio generator.
        """
        self._generate_basic_standard(sdi_qx)

        sdi_qx.generator.configure_audio_groups([1, 3, 5, 7], True)
        time.sleep(5)
        audio_state = sdi_qx.generator.audio
        for group in ['audioGroup1', 'audioGroup3', 'audioGroup5', 'audioGroup7']:
            assert audio_state['audioGroup'][group] is True

        sdi_qx.generator.configure_audio_groups([2, 4, 6, 8], True)
        audio_state = sdi_qx.generator.audio
        for group in ['audioGroup2', 'audioGroup4', 'audioGroup6', 'audioGroup8']:
            assert audio_state['audioGroup'][group] is True

        sdi_qx.generator.configure_audio_groups(list(range(1, 9)), False)
        audio_state = sdi_qx.generator.audio
        for group in ['audioGroup1', 'audioGroup2', 'audioGroup3', 'audioGroup4', 'audioGroup5', 'audioGroup6', 'audioGroup7', 'audioGroup8']:
            assert audio_state['audioGroup'][group] is False
