import pytest
import os
from test_system.factory import make_qx
from test_system.models.qxseries.operationmode import OperationMode
from test_system.models.qxseries.io import SDIIOType

generator = os.getenv('GENERATOR_QX')
analyser = os.getenv('ANALSYER_QX')
test = os.getenv('TEST_QX')
INPUT_FILE = 'testfile.txt'


def pattern(filename):
    # Generate list of patterns for given standard
    with open(INPUT_FILE) as f:
        read_data = f.read().split('\n')
    return read_data

    #return confidence_test_standards



#@pytest.fixture
#def generator_qx(test_generator_hostname):
#    generator_qx = make_qx(hostname=test_generator_hostname)
#    generator_qx.generator.bouncing_box = False
#    generator_qx.generator.output_copy = False
#    generator_qx.io.sdi_output_source = SDIIOType.BNC
#    generator_qx.io.set_sdi_outputs(('generator', 'generator', 'generator', 'generator'))



@pytest.mark.parametrize('pattern', pattern(INPUT_FILE))
def test_confidence(pattern): #confidence_test_standards):
    print(type(pattern))

    assert True
