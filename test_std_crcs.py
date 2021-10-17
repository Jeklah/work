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
@pytest.fixture
def gen_pattern_list(generator_qx, confidence_test_standards):
    try:
        test_patterns = generator_qx.generator.get_test_patterns(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3])
        for pattern in test_patterns:
            yield pattern
        #return test_patterns
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
    unpickled_crcs = pd.read_pickle('./crc_dataframe1.pkl')
    return unpickled_crcs


#@pytest.mark.sdi
#def test_patterns(generator_qx, analyser_qx, confidence_test_standards):
#    golden_master = unpickle_golden_master()
#    golden_standards = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards])]
#    qx_std_pattern_list = gen_pattern_list(generator_qx, confidence_test_standards)
#    pattern_counter = 0
#    qx_settled = False
#
#    for pattern in qx_std_pattern_list:
#
#        check_test_pattern = golden_standards.iat[pattern_counter, 1]
#        crc_list = golden_standards.iat[pattern_counter, 2]
#        pattern_counter += 1
#        print(f'golden_master info: test_pattern: {check_test_pattern}, crc: {crc_list}')
#        generator_qx.generator.set_generator(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
#        time.sleep(2)
#        qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
#        while qx_settled is False:
#            qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
#        index_counter = 0
#
#        for crc_response in analyser_qx.analyser.get_crc_analyser():
#            print(f'qx info. pattern: {pattern}, crc: {crc_list}')
#            print(f"golden master info. pattern: {check_test_pattern}, crc: {crc_response['activePictureCrc']}")
#
#            assert pattern == check_test_pattern.get(0)
#            assert crc_list[index_counter] == crc_response['activePictureCrc']
#            index_counter += 1


# this should be seperated up into multiple seperate parts to make it less complex and less nested loops if possible.
@pytest.mark.sdii
def test_crc_goldenmaster(generator_qx, analyser_qx, confidence_test_standards, gen_pattern_list):
    crc_check_index_list = []
    crc_check_list = []
    crc_count = []
    golden_master = unpickle_golden_master()
    qx_settled = False
    standards = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards])]
    print(standards)

    # confidence_test_standards_list = gen_std_list(generator_qx, std_filter='test')
    #pattern_list = gen_pattern_list(generator_qx, confidence_test_standards)
    pattern_counter = 0
    #for pattern in gen_pattern_list:

    crc_count = []
    check_test_patterns = standards.iat[pattern_counter, 1]
    crcs = standards.iat[pattern_counter, 2]
    pattern_counter += 1
    print(f'test pattern: {check_test_patterns}: crcs, {crcs}')

    generator_qx.generator.set_generator(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], gen_pattern_list)
    qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], gen_pattern_list)
    time.sleep(2)
    while qx_settled is False:
        time.sleep(2)
        qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], gen_pattern_list)
    index_counter = 0
    for crc_response in analyser_qx.analyser.get_crc_analyser():

            #print(crc_response)
        print(f"gold master crc number, index number {index_counter}: {crcs[index_counter]} qx crc: {crc_response['activePictureCrc']}", file=sys.stderr)
        assert crc_response['activePictureCrc'] != crcs[index_counter]
        index_counter += 1
            #wait = input('please push enter to continue')

        #print(f"{golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards])]}")
       # print(f'checking: {confidence_test_standards[1]}, {confidence_test_standards[2]}, {pattern}')
       # generator_qx.generator.set_generator(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)

       # # this can probably be replaced with test_system.retry
       # qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)
       # while qx_settled is False:
       #     time.sleep(1)
       #     qx_settled = generator_qx.generator.is_generating_standard(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3], pattern)

       # crc_count.append(get_crc_count(generator_qx))
       # try:
       #     # seperate the zips out in to seperate for loops and print out what the values are
       #     for count in crc_count:
       #         print(f'count: {count}')
       #         crc_index = crc_count.index(count)
       #     for crc_value in analyser_qx.analyser.get_crc_analyser():
       #         try:

       #                 crc_check_index_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards]) & \
       #                                                               golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'].index[crc_index])
       #                 crc_check_list.append(golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards]) & \
       #                                                         golden_master['Pattern'].apply(lambda y: y == [pattern])]['CrcValue'][crc_check_index_list[crc_index]])

       #                 print(f'crc_valuei from qx: {crc_value["activePictureCrc"]}')
       #                 print(f'standard: {confidence_test_standards}')
       #                 print(f'pattern: {pattern}')
       #                 print(f'index of crc in golden_master: {crc_check_index_list[crc_value]}')
       #                 try:
       #                     for (crc, index) in zip(crc_check_list, crc_check_index_list):
       #                         print(f'crc is: {crc}')
       #                         print(f'length of crc_check_list: {len(crc_check_list)}')
       #                         print(f'length of crc_check_index_list: {len(crc_check_index_list)}')
       #                         #print(f'crc check list crc: {str(crc_check_list[crc_check_index_list[index]]).strip("[]")}')
       #                         check_crc = crc_check_list[crc_check_index_list[index]] # fails here
       #                         print(f'check_crc: {check_crc}')
       #                         mod_check_crc = check_crc[index]
       #                         print(f'mod_check_crc: {mod_check_crc}')
       #                         print(f'mod_check_crc type: {type(mod_check_crc)}')
       #                         print(f'crc from golden master: {check_crc}')
       #                         print(type(crc_value["activePictureCrc"]))
       #                         print(type(mod_check_crc))
       #                         print(repr(crc_value["activePictureCrc"]))
       #                         print(repr(mod_check_crc))
       #                         assert crc_value["activePictureCrc"] == mod_check_crc     # this HAS to be correct. both strings, both appearing without quotes, no assertion failure.
       #                         # log.error(f'TEST FAILED: {crc_value} does not match stored value for {confidence_test_standards}: {pattern}')
       #                 except TestException as err:
       #                     log.error(f'An error occurred while checking CRC values: {err}')
       #         except TestException as listErr:
       #             log.error(f'An error occured while making crc lists: {listErr}')
       # except TestException as paraErr:
       #     log.error(f'An error occurred while setting confidence_test_standards parameters: {paraErr}')
