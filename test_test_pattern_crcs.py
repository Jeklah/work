"""
Testing nested tests to granularize the test.
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

# Setting up the test environment
@pytest.fixture(scope='module')
def generator_qx(test_generator_hostname):
    generator_qx = make_qx(hostname=test_generator_hostname)
    generator_qx.generator.bouncing_box = False
    generator_qx.generator.output_copy = False
    generator_qx.io.sdi_output_source = SDIIOType.BNC
    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))
    log.info(f'{generator_qx.hostname}: generator setup complete')
    yield generator_qx


@pytest.fixture(scope='module')
def analyser_qx(test_analyser_hostname):
    analyser_qx = make_qx(hostname=analyser)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


def unpickle_golden_master():
    golden_master = pd.read_pickle('./crc_dataframe1.pkl')
    return golden_master


# Get all test_patterns for a given standard
def gen_pattern_list(generator_qx, confidence_test_standards):
    try:
        test_patterns = generator_qx.generator.get_test_patterns(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3])
        return test_patterns
    except GeneratorException as pattErr:
        log.info(f'An error occurred while generating test_patterns: {pattErr}')


def test_crc_gold_master(generator_qx, analyser_qx, confidence_test_standards):
    golden_master = unpickle_golden_master()
    standard_df = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [confidence_test_standards])]
    standard = standard_df.iat[0, 0]

    pattern_list = gen_pattern_list(generator_qx, confidence_test_standards) #generator_qx.generator.get_test_patterns(confidence_test_standards[1], confidence_test_standards[2], confidence_test_standards[3])
    for pattern in pattern_list:
        print(f'checking {standard}, pattern: {pattern}')
        test_test_pattern(generator_qx, analyser_qx, standard, pattern, standard_df)



# might be going over the top. just do the necessary work in the relevant test.
# have deleted what i thought might be ott..
def test_test_pattern(generator_qx, analyser_qx, standard, pattern, standard_df):
    qx_settled = False
    generator_qx.generator.set_generator(standard[0][1], standard[0][2], standard[0][3], pattern)
    qx_settled = generator_qx.generator.is_generating_standard(standard[0][1], standard[0][2], standard[0][3], pattern)
    time.sleep(2)
    while qx_settled is False:
        time.sleep(2)
        qx_settled = generator_qx.generator.is_generating_standard(standard[0][1], standard[0][2], standard[0][3], pattern)

    print('test')
    pattern_crc_index = 0
    crc_response = analyser_qx.analyser.get_crc_analyser()
    for crc in crc_response:
        #if crc['activePictureCrc'] != "0":
        #    break
        time.sleep(1)
        print(f'pattern index: {pattern_crc_index}')
        expected_crc = standard_df.iat[pattern_crc_index, 2]
        expected_crc = expected_crc[pattern_crc_index].strip('[]')
        qx_crc = crc['activePictureCrc']
        print(f'expected crc: {expected_crc}, type: {type(expected_crc)}')
        print(f'qx crc: {qx_crc}, type: {type(qx_crc)}')
        pattern_crc_index += 1

        assert expected_crc == qx_crc
        # this does work but it is as christian said, when one pattern fails, it still fails the whole
        # standard.


