"""
Tests that validate that the SDI input / output configuration setting behave as expected.
"""

import logging
import time

import pytest

from autolib.factory import make_qx
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.logconfig import autolib_log
from autolib.models.qxseries.operationmode import OperationMode

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates generator qx object using test_generator_hostname global.
    """
    generator_qx = make_qx(test_generator_hostname)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.set_sdi_input_source = SDIIOType.BNC
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    log.info(f"FIXTURE: Qx {generator_qx.hostname} setup complete")
    yield generator_qx
    # Make sure the Qx SDI outputs are all generator after test
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    log.info(f"FIXTURE: Qx {generator_qx.hostname} teardown complete")


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    """
    Creates analyser qx object using test_analyser_hostname global.
    """
    analyser_qx = make_qx(test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} setup complete")
    yield analyser_qx
    log.info(f"FIXTURE: Qx {analyser_qx.hostname} teardown complete")


def generator_configs():
    """
    Yield all possible combinations of generator output modes.
    """
    outputs = ['generator', 'off']
    for a in outputs:
        for b in outputs:
            for c in outputs:
                for d in outputs:
                    yield a, b, c, d


@pytest.mark.sdi_stress
class TestSdiInputOutput:
    """
    Suite of tests that exercise the SDI output configurations of the Qx / QxL.
    """
    @pytest.mark.skip('Incomplete test')
    @pytest.mark.parametrize('output_config', generator_configs())
    def test_outputs(self, output_config, generator_qx):
        """
        Validate that all combinations of SDI output mode for spigots A-D behave as expected.
        """
        generator_qx.request_capability(OperationMode.SDI_STRESS)

        test_standard = "1920x1080p50", "YCbCr:422:10", "3G_A_Rec.709", "100% Bars"
        generator_qx.generator.bouncing_box = False
        generator_qx.generator.output_copy = False
        generator_qx.io.set_sdi_output_source(output_config)
        generator_qx.generator.set_generator(*test_standard)

        time.sleep(5)
        assert generator_qx.generator.is_generating_standard(*test_standard)

        # TODO We now need to see whether each output is giving the right data as far as the analyser can determine.

    def test_output_copy(self, generator_qx, analyser_qx):
        """
        Check that output copy produces copies of the generated standard across all four outputs. We can use the fact
        that the Qx cannot distinguish between four independent 1920x1080 3G signals and the four components of a 3G QL
        UHD standard. Then turn off output copy and confirm that the standard is the 3G standard (A only).
        """
        generator_qx.request_capability(OperationMode.SDI_STRESS)
        analyser_qx.request_capability(OperationMode.SDI_STRESS)
        single_link_3g_standard = "1920x1080p50", "YCbCr:422:10", "3G_A_Rec.709", "100% Bars"
        quad_link_3g_standard = "3840x2160p50", "YCbCr:422:10", "QL_3G_A_SQ_Rec.709", "100% Bars"

        generator_qx.generator.bouncing_box = False
        generator_qx.generator.output_copy = True

        generator_qx.generator.set_generator(*single_link_3g_standard)

        time.sleep(5)
        assert generator_qx.generator.is_generating_standard(*single_link_3g_standard)
        assert analyser_qx.analyser.sdi.get_analyser_status() == quad_link_3g_standard[:3]

        generator_qx.generator.output_copy = False

        time.sleep(5)
        assert generator_qx.generator.is_generating_standard(*single_link_3g_standard)
        assert analyser_qx.analyser.sdi.get_analyser_status() == single_link_3g_standard[:3]
