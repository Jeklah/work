"""
Tests that validate the the insertion of SMPTE ST 352 Payload Identification Code ancillary packets from the Qx / QxL
SDI generator.
"""

import logging
import time

import pytest
from typing import Generator, List, Tuple
from autolib.factory import make_qx, Qx
from autolib.models.qxseries.analyser import ParsedStandard
from autolib.models.qxseries.qxexception import QxException
from autolib.models.qxseries.input_output import SDIIOType, SDIOutputSource
from autolib.models.qxseries.operationmode import OperationMode
from autolib.testexception import TestException
from autolib.logconfig import autolib_log

log = logging.getLogger(autolib_log)


def make_sdi_unit(host: str) -> Qx:
    """
    Create a Qx object using the supplied hostname configured to operate in SDI mode
    with SDI outputs and return it.

    :param host:    Hostname of Qx unit to create
    :return:        Qx object representing the supplied hostname
    """
    qx = make_qx(host)
    qx.request_capability(OperationMode.SDI)
    qx.io.sdi_output_source = SDIIOType.BNC
    return qx


@pytest.fixture
def generator_unit(test_generator_hostname: str) -> Generator[Qx, None, None]:
    """
    Provide a Qx configured for the test run to act as a generator.

    Pytest fixture that will create a Qx object using the test_generator_hostname global fixture and setup the unit
    before the test run and then perform teardown operations afterward.

    :param test_generator_hostname:  Hostname of Qx unit to create
    """
    generator_qx = make_sdi_unit(test_generator_hostname)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.set_sdi_output_source = SDIIOType.BNC, (SDIOutputSource.GENERATOR, ) * 4
    log.info(f"FIXTURE: Generator Qx {generator_qx.hostname} setup complete")
    yield generator_qx
    # No teardown is needed
    log.info(f"FIXTURE: Generator Qx {generator_qx.hostname} teardown complete")


@pytest.fixture
def analyser_unit(test_analyser_hostname: str) -> Generator[Qx, None, None]:
    """
    Provide a Qx configured for the test run to act as an analyser.

    Pytest fixture that will create a Qx object using the test_analyser_hostname global fixture and setup the unit
    before the test run and then perform teardown operations afterward.

    :param test_analyser_hostname:  Hostname of Qx unit to create
    """
    analyser_qx = make_sdi_unit(test_analyser_hostname)
    analyser_qx.io.set_sdi_input_source = SDIIOType.BNC
    log.info(f"FIXTURE: Analyser Qx {analyser_qx.hostname} setup complete")
    yield analyser_qx
    # No teardown is needed
    log.info(f"FIXTURE: Analyser Qx {analyser_qx.hostname} teardown complete")


def _generate_expected_s352_locations(qx_analyser: Qx) -> Generator[tuple, None, None]:
    """
    Generator object to determine all expected st352 packet locations based on incoming standard. Used to parameterise
    `test_s352_location` test

    :param qx_analyser:  Hostname Qx of analyser unit used during testing
    """

    s352_locations = {
        525: {"i": [13, 276], "p": [13]},
        625: {"i": [9, 322], "p": [9]},
        750: {"p": [10]},
        1125: {"i": [10, 572], "p": [10], "psf": [10, 572]}
    }

    # Get the current analysed video standard information and split into appropriate vars. Use to determine
    # expected st352 locations
    parsed_analysed_standard = ParsedStandard(
        qx_analyser.analyser.sdi.analyser_status.get('standard', None))

    resolution = parsed_analysed_standard.api_resolution
    scan_type = f'{parsed_analysed_standard.frame_rate}{parsed_analysed_standard.frame_type.value}'
    link_count = parsed_analysed_standard.links
    data_rate = parsed_analysed_standard.data_rate
    standard_level = parsed_analysed_standard.level
    frame_type = parsed_analysed_standard.frame_type
    # Use analysed standard data to determine which sub-images SHOULD contain a 352 packet
    if standard_level == "A":
        if data_rate <= 3.0 and link_count == 1:
            sub_image_search = ["subImage1"]
        elif data_rate > 3.0 and link_count > 1:
            sub_image_search = ["subImage1", "subImage2", "subImage3", "subImage4"]
        elif link_count == 2:
            sub_image_search = ["subImage1"]
        else:
            sub_image_search = ["subImage1", "subImage2", "subImage3", "subImage4"]
            log.error(f"{qx_analyser.hostname} - Assuming QL 3GA: {data_rate}")
    elif standard_level == "B":
        if data_rate <= 3.0 and link_count == 1:
            sub_image_search = ["subImage1", "linkBSubImage1"]
        elif data_rate <= 3.0 and link_count == 2:
            sub_image_search = ["subImage1", "subImage2", "linkBSubImage1", "linkBSubImage2"]
        elif data_rate >= 3.0 and link_count == 4:
            sub_image_search = ["subImage1", "subImage2", "subImage3", "subImage4",
                                "linkBSubImage1", "linkBSubImage2", "linkBSubImage3", "linkBSubImage4"]
        else:
            raise TestException(f"{qx_analyser.hostname} - Failed to determine sub_img_search [LVL B]: {data_rate}")
    elif standard_level is None or standard_level == "N/A":
        standard_level = "N/A"
        sub_image_search = []
    else:
        raise TestException(f"{qx_analyser.hostname} - Unrecognised standard level: {standard_level}")

    # Derive line number
    if 525 < int(resolution[1]) < 720:
        line_num = 525
    elif 720 >= int(resolution[1]) < 1080:
        line_num = 750
    elif int(resolution[1]) >= 1080:
        line_num = 1125
    else:
        raise QxException(f"Invalid resolution requested: {resolution[1]}")

    # Test d2383: Generating level B standards the payload Id ancillary packet is not being inserted correctly
    # https://phabrix.axosoft.com/viewitem?id=2383&type=defects&force_use_number=true
    # Test d2432: ST 352 - (6G single link) packets should not appear in the C channel
    # https://phabrix.axosoft.com/viewitem?id=2432&type=defects&force_use_number=true
    # if line_num == 750 and frame_type.value == "i":
    #     print("This standard does not have a s352 packet.")
    #     return

    if data_rate == 1.5 or standard_level == "B" or data_rate == 6.0 and link_count == 1:
        # Set expected lines for level B standards
        s352_exp_line = [10, 572] if standard_level == "B" else s352_locations[line_num][frame_type.value]
        # Set expected channel locations for 1.5G || level B standard || 6G single standards
        s352_exp_channel = ["yPos"]
    else:
        s352_exp_line = s352_locations[line_num][frame_type.value]
        s352_exp_channel = ["yPos", "cPos"]

    # Calculate the number of expected results we should get based on the analysed standard
    no_of_results = (len(s352_exp_line) * len(s352_exp_channel)) * len(sub_image_search)

    # @DUNC This is horrible - we need to configure the logger to automatically emit stuff like the analyser
    # hostname automatically

    # Log the expected st352 line / channel / sub-image locations and the data used to deduce
    log.info(f"{qx_analyser.hostname} - Line number for {resolution} assigned as {line_num}")
    log.info(f"{qx_analyser.hostname} - Analysed standard is level {standard_level}")
    log.info(f"{qx_analyser.hostname} - Analysed standard data rate is {data_rate} with {link_count} links")
    log.info(f"{qx_analyser.hostname} - Expected number of 352 packets is {no_of_results}")
    log.info(f"{qx_analyser.hostname} - Looking in sub images: {sub_image_search}")
    log.info(f"{qx_analyser.hostname} - s352 packet is expected on line(s) {s352_exp_line}")
    log.info(f"{qx_analyser.hostname} - s352 packet is expected on channel(s) {s352_exp_channel}")

    for sub_image in sub_image_search:
        for line in s352_exp_line:
            for channel in s352_exp_channel:
                yield sub_image, line, channel


@pytest.mark.sdi_stress
@pytest.mark.timeout(600, method='thread')
def test_s352_location_confidence(confidence_test_standards: List[Tuple], generator_unit: Qx, analyser_unit: Qx):
    """
    Confirm SMPTE ST 352 Payload ID code ANC packets are inserted on the correct lines for all confidence test video
    standards.

    :param confidence_test_standards:   Pytest fixture that returns a list of confidence test standards to test
    :param generator_unit:              Pytest fixture that returns a Qx object configured as a generator
    :param analyser_unit:               Pytest fixture that returns a Qx object configured as an analyser
    """

    # Ensure we're in the right mode to run the test on both units
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _check_s352_location(confidence_test_standards,
                         generator_unit, analyser_unit)


@pytest.mark.slow
@pytest.mark.sdi_stress
@pytest.mark.timeout(6000, method='thread')
def test_s352_location_full(all_standards: List[Tuple], generator_unit: Qx, analyser_unit: Qx):
    """
    Confirm SMPTE ST 352 Payload ID code ANC packets are inserted on the correct lines for all supported video
    standards. This test takes many hours and as such should be a scheduled run in quiet hours or run in response to
    a direct bug.

    :param all_standards:   Pytest fixture that returns a list of all supported video standards to test
    :param generator_unit:  Pytest fixture that returns a Qx object configured as a generator
    :param analyser_unit:   Pytest fixture that returns a Qx object configured as an analyser
    """
    # Ensure we're in the right mode to run the test on both units
    generator_unit.request_capability(OperationMode.SDI_STRESS)
    analyser_unit.request_capability(OperationMode.SDI_STRESS)
    _check_s352_location(all_standards, generator_unit, analyser_unit)


def _check_s352_location(standards_list: List[Tuple], generator_qx: Qx, analyser_qx: Qx):
    """
    Prove that the Qx signal generator is inserting SMPTE 352 ancillary packets on the correct line for each test
    standard. This function implements the actual test as is called by the parameterised PyTest test wrapper functions.

    Take expected values generated based on current standard being received by the unit and configure the ancillary
    inspector to catch the supplied 352 packet in that location ONLY.

    Test will pass with the existence of a packet based on the logic that the search criteria is precise enough but
    further work can be done to validate the data inside the ancillary packet once it is caught.

    :param standards_list:  List of standards to test
    :param generator_qx:    Qx object configured as a generator
    :param analyser_qx:     Qx object configured as an analyser
    """

    log.info(
        f'{generator_qx.hostname} - Configure generator to use current standard data - {standards_list}')

    # Configure the generator
    generator_qx.generator.set_generator(standards_list[1], standards_list[2], standards_list[3])
    # Allow generator time to settle after generation of standard
    time.sleep(5)

    # Make sure we're not only triggering on errors
    generator_qx.anc.trigger_only_on_errors = False

    # Iterate through the expected location data for the current standard
    for subimg, line, channel in _generate_expected_s352_locations(analyser_qx):

        log.info(f"Configure ANC inspector: {subimg} - {line} - {channel}")

        # Configure the ANC inspector to identify s352 anc packets using did + sdid
        analyser_qx.anc.setup_inspector(identifier=("custom", 1, 65), subimage=subimg, position=channel, range=("inside", line-1, line+1))

        # Allow the ANC inspector an acceptable amount of time to catch the desired ancillary packet
        time.sleep(2)

        # Get the found_in data for s352
        anc_insp_data = analyser_qx.anc.inspect(found_in=True)
        log.info(f"{analyser_qx.hostname} - {anc_insp_data}")

        # Verify the caught s352 packet data reports expected location
        assert anc_insp_data, "The anc inspector did not find the 352 packet"
        assert anc_insp_data[0]['line'] == line
        assert anc_insp_data[0]['channel'] == 'Y-Pos' if channel == 'yPos' else 'C-Pos' if channel == 'cPos' else False
