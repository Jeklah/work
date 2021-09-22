"""
This test will generate a list of standards and check that the CRCs
for each test pattern that are contained in the standard matches
up with what we have on record for each standard and each test pattern.
"""
import os
import sys
import time
import pytest
import logging
import pandas as pd
if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')
from test_system.factory import make_qx
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType
from test_system.logconfig import test_system_log
from test_system.models.qxseries.analyser import AnalyserException
from test_system.models.qxseries.generator import GeneratorException
from test_system.models.qxseries.qxexception import QxException
from test_system.testexception import TestException

# Set up logging
log = logging.getLogger(test_system_log)

# Get ENV Variables
generator = os.getenv('GENERATOR_QX')
analyser = os.getenv('ANALYSER_QX')
test = os.getenv('TEST_QX')


# Setting up the test environment.
@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    generator_qx = make_qx(hostname=generator)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.sdi_output_source = SDIIOType.BNC
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'{generator_qx.hostname}: CRC Verification Test Generator Setup Complete.')
    yield generator_qx


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    analyser_qx = make_qx(hostname=analyser)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: CRC Verification Test Analyser Setup Complete.')
    yield analyser_qx


# Setting up filters and populating the standard list.
@pytest.mark.sdi
def gen_confidence_test_standards_list(generator_qx, std_filter='confidence_test_standards'):
    if not generator_qx.query_capability(OperationMode.IP_2110):
        if std_filter == 'nightly':  # Nightly filter, requirements agreed upon in meeting.
            standards_list = generator_qx.generator.get_matching_standards(
                [1.5],
                r"720.*|1920.*|2048.*|3840.*|4096.*",
                r"RGB.*|YCbCr:422:10|YCbCr:422:12|YCbCr:444:.*",
                r".*709|.*2020|HLG.*|PQ.*|S-Log3.*",
            )
        elif std_filter == 'test':
            standards_list = generator_qx.generator.get_matching_standards(
                [1.5], r"1920.*", r"YCbCr:422:10", r".*709"
            )
        elif std_filter == 'fast':
            standards_list = generator_qx.generator.get_matching_standards(
                [1.5, 3.0],
                r"(1920x1080|1280x720)[i|p]50",
                "YCbCr:422:10",
                ".Rec.709"
            )
        elif std_filter == 'confidence_test_standards':
            standards_list = generator_qx.generator.get_matching_standards(
                [1.5, 3.0, 6.0, 12.0],
                r"\d+x\d+p\d+",
                r"YCbCr:422:10",
                r".*709"
            )
        elif std_filter == 'all':
            all_confidence_test_standardss = generator_qx.generator.get_standards()
            standards_list = [
                [data_rate, resolution, colour_map, gamut]
                for data_rate in all_confidence_test_standardss
                for resolution in all_confidence_test_standardss[data_rate]
                for colour_map in all_confidence_test_standardss[data_rate][resolution]
                for gamut in all_confidence_test_standardss[data_rate][resolution][colour_map]
            ]
    else:
        print(f'{generator_qx.hostname} is currently in IP 2110 mode. Please switch to SDI mode.')
    yield standards_list


# Get all test patterns for a given standard.
@pytest.mark.sdi
def gen_pattern_list(generator_qx, confidence_test_standards):
    try:
        test_patterns = generator_qx.generator.get_test_patterns(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3])
        return test_patterns
    except GeneratorException as pattErr:
        log.error(f'An error occurred while generating test_patterns: {pattErr}')


# Get all subimages for a given standard.
@pytest.mark.sdi
def gen_subimages_list(generator_qx, confidence_test_standards):
    confidence_test_standards_lvl, data_rate, links = (
        generator_qx.analyser.parse_analyser_status(generator_qx.analyser.get_analyser_status())[
            'type'
        ]['level'],
        generator_qx.analyser.parse_analyser_status(generator_qx.analyser.get_analyser_status())[
            'type'
        ]['data_rate_Gb'],
        generator_qx.analyser.parse_analyser_status(generator_qx.analyser.get_analyser_status())[
            'type'
        ]['link_number'],
    )
    if confidence_test_standards_lvl == 'A':
        if data_rate <= 3.0 and links == 1:
            sub_images = ['subImage1']
        elif data_rate <= 3.0 and links > 3:
            sub_images = ['subImage1', 'subImage2', 'subImage3', 'subImage4']
        elif links == 2:
            sub_images = ['subImage1']
        else:
            sub_images = ['subImage1', 'subImage2', 'subImage3', 'subImage4']
            log.error(f'{generator_qx.hostname} - Assuming QL 3GA: {data_rate}')
    elif confidence_test_standards_lvl == 'B':
        if data_rate >= 3.0 and links == 1:
            sub_images = ['subImage1', 'linkBSubImage1']
        elif data_rate >= 3.0 and links == 4:
            sub_images = ['subImage1', 'subImage2', 'subImage3', 'subImage4',
                          'linkBSubImage1', 'linkBSubImage2', 'linkBSubImage3', 'linkBSubImage4']
        else:
            raise TestException(f'{generator_qx.hostname} - Failed to determine sub images [LVL B]: {data_rate}')
    else:
        raise TestException(f'{generator_qx.hostname} - Unrecognised standard level: {confidence_test_standards_lvl}')
    return sub_images


def get_crc_count(generator_qx):
    crc_count = len(generator_qx.analyser.get_crc_analyser())
    return crc_count


def unpickle_golden_master():
    unpickled_crcs = pd.read_pickle('./crc_dataframe.pkl')
    return unpickled_crcs


@pytest.mark.sdi
def test_Crc_goldenmaster(generator_qx, analyser_qx, confidence_test_standards):
    crc_check_index_list = []
    crc_check_list = []
    crc_count = []
    golden_master = unpickle_golden_master()
    qx_settled = False
    # confidence_test_standards_list = gen_std_list(generator_qx, std_filter='test')
    # for param in confidence_test_standards:
    pattern_list = gen_pattern_list(generator_qx, confidence_test_standards)
    for pattern in pattern_list:
        print(f'checking: {confidence_test_standards[1]}, {confidence_test_standards[2]}, {confidence_test_standards[2]}, {pattern}')
        generator_qx.generator.set_generator(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
        qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
        time.sleep(1)
        while qx_settled is False:
            qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
        crc_count.append(get_crc_count(generator_qx))
        #confidence_test_standards_params = list(confidence_test_standards)
        try:
            for (index, crc_value) in zip(crc_count, analyser_qx.analyser.get_crc_analyser()):
                try:
                    crc_check_index_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards]) & \
                                                                  golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'].index[index])
                    crc_check_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards]) & \
                                                            golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'][crc_check_index_list[index]])
                    try:
                        for (crc, index) in zip(crc_check_list, crc_check_index_list):
                            print(f'crc is: {crc}')
                            assert crc_value == crc_check_list[crc_check_index_list[index]]
                               #log.error(f'TEST FAILED: {crc_value} does not match stored value for {confidence_test_standards}: {pattern}')
                    except TestException as err:
                        log.error(f'An error occurred while checking CRC values: {err}')
                except TestException as listErr:
                    log.error(f'An error occured while making crc lists: {listErr}')
        except TestException as paraErr:
            log.error(f'An error occurred while setting confidence_test_standards parameters: {paraErr}')
