"""
Tests that validate that the CRC analyser features behave as expected.    
"""

import logging
import time

import pytest

from autolib.factory import make_qx
from autolib.logconfig import autolib_log
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode

log = logging.getLogger(autolib_log)


@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    """
    Creates generator qx object using test_generator_hostname global.
    """
    generator_qx = make_qx(test_generator_hostname)
    generator_qx.request_capability(OperationMode.SDI_STRESS)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.generator.jitter_insertion("Disabled", 0.01, 10)
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    log.info(f"FIXTURE: Qx {generator_qx.hostname} setup complete")
    yield generator_qx
    generator_qx.generator.bouncing_box = False
    log.info(f"FIXTURE: Qx {generator_qx.hostname} teardown complete")


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
def test_active_image_crc_bbox(generator_qx, analyser_qx, confidence_test_standards):
    """
    Check that the CRC analyser can spot differences in the analysed input when the bouncing box is enabled and
    disabled in the confidence_test_standards range of standards.

    * Generate a range of standards supplied by the confidence_test_standards global fixture in conftest.py
    * Disable the bouncing box
    * Get active picture CRC at analyser unit
    * Enable the bouncing box
    * Get active picture CRC at analyser unit
    * Compare all subimage CRCs to ensure that at least one is different (depending on the position of the box this
      value could be 1 - 4 depending on the standard).
    """

    _, res, colour_map, gam = confidence_test_standards
    generator_qx.generator.set_generator(res, colour_map, gam)
    generator_qx.generator.bouncing_box = False
    time.sleep(5)

    assert analyser_qx.analyser.sdi.expected_video_analyser(res, colour_map, gam)

    crc_no_bbox = generator_qx.analyser.sdi.get_link_and_subimage_crcs()
    generator_qx.generator.bouncing_box = True
    time.sleep(1)

    crc_with_bbox = analyser_qx.analyser.sdi.get_link_and_subimage_crcs()

    assert len(crc_with_bbox) == len(crc_no_bbox)  # Sanity check that we still have the same number of subimages

    differences = 0
    sub_image_crcs = ""
    for bb_sub_image, nbb_sub_image in zip(crc_with_bbox, crc_no_bbox):
        bb_sub_image_crc = bb_sub_image.get('activePictureCrc', None)
        nbb_sub_image_crc = nbb_sub_image.get('activePictureCrc', None)
        if bb_sub_image_crc != nbb_sub_image_crc:
            differences += 1
        sub_image_crcs += f" ({bb_sub_image_crc}, {nbb_sub_image_crc}) "

    log.info(f'Standard {" ".join([str(x) for x in confidence_test_standards])} - CRCs (with, without bbox): [{sub_image_crcs}]')
    assert differences > 0


@pytest.mark.sdi_stress
def test_crc_consistency(generator_qx, analyser_qx, confidence_test_standards):
    """
    Check that the CRC analyser gives consistent readings before and after a change of input standard.

    * Disable the bouncing box
    * Generate a range of standards supplied by the confidence_test_standards global fixture in conftest.py
    * Get active picture CRC at analyser unit
    * Generate a new standard
    * Generate the original test standard
    * Get active picture CRC at analyser unit
    * Compare all subimage CRCs to ensure that all are the same.
    """
    generator_qx.request_capability(OperationMode.SDI_STRESS)
    analyser_qx.request_capability(OperationMode.SDI_STRESS)

    _, res, colour_map, gam = confidence_test_standards
    generator_qx.generator.bouncing_box = False

    # Standard under test
    generator_qx.generator.set_generator(res, colour_map, gam)
    time.sleep(5)
    assert analyser_qx.analyser.sdi.expected_video_analyser(res, colour_map, gam)
    crc_before = generator_qx.analyser.sdi.get_link_and_subimage_crcs()

    # Standard to switch to in between (not a standard used in this test)
    interim_standard = "2048x1080p30", "RGBA:4444:10", "3G_A_HLG_Rec.2020"
    generator_qx.generator.set_generator(*interim_standard)
    time.sleep(5)
    assert analyser_qx.analyser.sdi.expected_video_analyser(*interim_standard)

    # Standard under test
    generator_qx.generator.set_generator(res, colour_map, gam)
    time.sleep(5)
    assert analyser_qx.analyser.sdi.expected_video_analyser(res, colour_map, gam)
    crc_after = generator_qx.analyser.sdi.get_link_and_subimage_crcs()

    assert len(crc_before) == len(crc_after)  # Sanity check that we still have the same number of subimages

    differences = 0
    sub_image_crcs = ""
    for crc_b_sub_image, crc_a_sub_image in zip(crc_before, crc_after):
        crc_b_sub_image_crc = crc_b_sub_image.get('activePictureCrc', None)
        crc_a_sub_image_crc = crc_a_sub_image.get('activePictureCrc', None)
        if crc_b_sub_image_crc != crc_a_sub_image_crc:
            differences += 1
        sub_image_crcs += f" ({crc_b_sub_image_crc}, {crc_a_sub_image_crc}) "

    log.info(f'Standard {" ".join([str(x) for x in confidence_test_standards])} - CRCs (before, after): [{sub_image_crcs}]')
    assert differences == 0
