"""\
Tests to confirm that the AES methods behave as expected against a real Qx.

These tests require a Qx type device to be available so should not be run by CI. As such
a marker has been applied to indicate this.
"""

import os
import pytest

import autolib.coreexception
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
    original_aes_config = qx.aesio.get_aes_config()
    yield qx
    qx.aesio.set_aes_config(original_aes_config)


@pytest.mark.requires_device
class TestSDIAES:
    def test_aes_config(self, sdi_qx):
        aes_config = sdi_qx.aesio.get_aes_config()
        assert aes_config.keys() >= {'aes1': {'mode': 'off'},
                                     'aes2': {'mode': 'off'},
                                     'aes3': {'mode': 'off'},
                                     'aes4': {'mode': 'off'},
                                     'passthroughConfigValid': False,
                                     'passthroughSource': 'aes1'}.keys()

    def test_aes_set_aes_config_sad_missing_items(self, sdi_qx):
        with pytest.raises(autolib.coreexception.CoreException):
            sdi_qx.aesio.set_aes_config({'aes1': {'mode': 'off'},
                                         'aes2': {'mode': 'off'},
                                         'aes3': {'mode': 'off'},
                                         'aes4': {'mode': 'transmit'}})

        with pytest.raises(autolib.coreexception.CoreException):
            sdi_qx.aesio.set_aes_config({'aes1': {'mode': 'transmit'},
                                         'aes2': {'mode': 'off'},
                                         'aes3': {'mode': 'off'},
                                         'aes4': {'mode': 'off'}})

    def test_aes_set_aes_config_transmit(self, sdi_qx):
        sdi_qx.aesio.set_aes_config({
            "aes1": {
                "group": 1,
                "mode": "transmit",
                "pair": 1,
                "transmitSource": "generator"
            },
            "aes2": {
                "group": 2,
                "mode": "transmit",
                "pair": 2,
                "transmitSource": "generator"
            },
            "aes3": {
                "group": 3,
                "mode": "transmit",
                "pair": 1,
                "transmitSource": "generator"
            },
            "aes4": {
                "group": 4,
                "mode": "transmit",
                "pair": 2,
                "transmitSource": "generator"
            }
        })

        aes_config = sdi_qx.aesio.get_aes_config()
        assert aes_config.get('aes1').get('mode') == 'transmit'
        assert aes_config.get('aes2').get('mode') == 'transmit'
        assert aes_config.get('aes3').get('mode') == 'transmit'
        assert aes_config.get('aes4').get('mode') == 'transmit'
