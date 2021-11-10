"""
An attempt at implementation of the test suite not using assert.
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

TEST_FAILED = False
TESTS_OUTPUT = []

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
    analyser_qx = make_qx(hostname=test_analyser_hostname)
    analyser_qx.io.sdi_output_source = SDIIOType.BNC
    log.info(f'{analyser_qx.hostname}: analyser setup complete')
    yield analyser_qx


def load_file(input_file):
    with open(input_file) as loader:
        input_lines = loader.read().split('\n')

    loaded_stds = []
    for line in input_lines:
        loaded_stds.append(line.split(','))

    #print(type(loaded_stds[0][3]))
    #print(loaded_stds[0][3])

    data_rate = float(loaded_stds[0][0])
    resolution = loaded_stds[0][1]
    mapping = loaded_stds[0][2]
    gamut = loaded_stds[0][3]

    return (f'{data_rate}, {resolution}, {mapping}, {gamut}')
    #print((f'{data_rate}, {resolution}, {mapping}, {gamut}'))

@pytest.fixture
def golden_master():
    return pd.read_pickle('./crc_dataframe1.pkl')


@pytest.mark.parametrize('standard', load_file('./standards.txt'))
def test_crcs_no_assert(generator_qx, analyser_qx, standard, golden_master):
    patterns = generator_qx.generator.get_test_patterns(standard[1], standard[2], standard[3])
    standard_df = golden_master.loc[golden_master['Standard'].apply(lambda x: x == [standard])]

    print(standard)
    for patt in patterns:
        generator_qx.generator.set_generator(standard[1], standard[2], standard[3], patt)
        time.sleep(2)
        qx_settled = generator_qx.generator.is_generating_standard(standard[1], standard[2], standard[3], patt)
        while qx_settled is False:
            qx_settled = generator_qx.generator.is_generating_standard(standard[1], standard[2], standard[3], patt)
        crc_index_gm = 0

        for crc_response in analyser_qx.analyser.get_crc_analyser():

            qx_crc = crc_response['activePictureCrc']
            expected_crc = standard_df.iat[0, 2][crc_index_gm]
            crc_index_gm += 1

            output_entry = [standard, patt, expected_crc, qx_crc]
            if qx_crc == expected_crc:
                output_entry.append('PASS')
            else:
                TEST_FAILED = True
                output_entry.append('FAIL')

            TESTS_OUTPUT.append(output_entry)



def test_results():
    with open('results', 'w') as f:
        for entry in TESTS_OUTPUT:
            print(entry, file=f)

    assert TEST_FAILED is False










load_file('./standards.txt')







